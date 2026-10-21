/** Migrate the legacy subagent filter to a dedicated leaf Agent Preset. */
const SUBAGENT = '@deepseek-ai/dsh-tool-subagent';
const BLOCKED = new Set([
  SUBAGENT, '@deepseek-ai/dsh-tool-subagent-control',
  '@deepseek-ai/dsh-tool-subagent-control/list-agents',
  '@deepseek-ai/dsh-workflow-worker-thread', '@deepseek-ai/dsh-workflow-ptc',
  '@deepseek-ai/dsh-tool-workflow', '@deepseek-ai/dsh-tool-ralph',
]);

export function compatiblePresets(definition) {
  let needsWorker = false;
  const workerId = `${definition.id}-worker`;
  function migrate(rows) {
    return rows.map(row => {
      const out = structuredClone(row);
      if (out.group === true) out.config = migrate(out.config);
      if (out.name !== SUBAGENT) return out;
      const config = out.config ?? {};
      if (Object.hasOwn(config, 'toolFilter')) {
        const filter = config.toolFilter;
        const deny = filter?.deny;
        if (config.provider !== 'spawn' || !filter || Object.keys(filter).length !== 1
          || !Array.isArray(deny) || deny.length !== 3
          || [...deny].sort().join(',') !== 'ralph,subagent_fork,workflow'
          || Object.hasOwn(config, 'persona') || config.agentPreset || config.allowedAgentPresets) {
          throw new Error('Unsupported custom subagent filter; preserve it and migrate manually');
        }
        delete config.toolFilter;
        config.agentPreset = workerId;
        config.maxDepth = Math.min(typeof config.maxDepth === 'number' ? config.maxDepth : 1, 1);
        needsWorker = true;
      }
      delete config.backgroundMode; // removed by the managed activation API
      out.config = config;
      return out;
    });
  }
  const parent = { ...definition, plugins: migrate(definition.plugins) };
  if (!needsWorker) return [parent];
  function leafRows(rows) {
    return rows.filter(row => !BLOCKED.has(row.name)).map(row => {
      const out = structuredClone(row);
      if (out.group === true) out.config = leafRows(out.config);
      if (out.name === '@deepseek-ai/dsh-persona') {
        out.config = { ...out.config, prefix: 'You are an execution worker. Complete only the task assigned by the parent within its authorized scope. Use the available tools directly. Do not create subagents, workflows, or autonomous loops. Report results and failures accurately.' };
      }
      return out;
    }).filter(row => row.group !== true || row.config.length > 0);
  }
  const worker = {
    id: workerId, name: '红队执行角色（无委派工具）',
    description: '供红队主会话调用的叶子执行角色，不提供子智能体、工作流或循环委派工具。',
    order: (definition.order ?? 10) + 1,
    plugins: leafRows(parent.plugins),
  };
  return [worker, parent];
}

export async function registerCompatiblePresets(registry, definition) {
  const releases = [];
  const cleanup = async () => {
    const errors = [];
    for (const release of releases.splice(0).reverse()) {
      try { await release(); } catch (error) { errors.push(error); }
    }
    if (errors.length) throw new AggregateError(errors, 'Preset cleanup failed');
  };
  try {
    for (const preset of compatiblePresets(definition)) {
      releases.push(await registry.register(preset));
      const row = (await registry.list()).find(item => item.id === preset.id);
      if (row?.broken) throw new Error(`${preset.id}: ${row.broken}`);
    }
    return cleanup;
  } catch (error) {
    await cleanup();
    throw error;
  }
}
