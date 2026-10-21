import datetime, pathlib, re, shutil, sys

dsh_root = pathlib.Path(sys.argv[1]).resolve()
roots = [dsh_root / 'plugins/dsh-purge',
         dsh_root / 'profiles/desktop/node_modules/dsh-purge']
old = 'Your working directory is {{cwd}}.'
new = 'Use the current session working directory for relative paths.'
old_const = f'const CWD_ONLY_SUFFIX = "{old}";'
new_const = f'const CWD_ONLY_SUFFIX = "{new}";'
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')

for root in roots:
    js = root / 'lib/identity.js'
    yaml = root / 'cordis.patch.yml'
    code = js.read_text(encoding='utf-8-sig')
    patch = yaml.read_text(encoding='utf-8-sig')
    if old_const not in code and new_const not in code:
        raise RuntimeError(f'未知插件结构，不做盲目替换：{js}')
    if f'personaSuffix: {old}' not in patch and f'personaSuffix: {new}' not in patch:
        raise RuntimeError(f'未知 personaSuffix，请人工检查：{yaml}')
    a = code.index('function isCwdOnlyText(')
    b = code.index('\nfunction looksLikeOfficialIdentity', a)
    replacement = '''function isCwdOnlyText(text) {
  const t = String(text || "").trim();
  return t === CWD_ONLY_SUFFIX
    || t === "Your working directory is {{cwd}}."
    || t === "Working directory: {{cwd}}."
    || t === "Working directory: {{cwd}}";
}
'''
    updated = (code[:a] + replacement + code[b:]).replace(old_const, new_const)
    new_patch = patch.replace(f'personaSuffix: {old}', f'personaSuffix: {new}')
    for file, before, after in [(js, code, updated), (yaml, patch, new_patch)]:
        if before == after:
            print('ALREADY FIXED', file)
            continue
        shutil.copy2(file, str(file) + '.backup-' + stamp)
        file.write_text(after, encoding='utf-8')
        print('UPDATED', file)
    assert new_const in js.read_text(encoding='utf-8')
    assert f'personaSuffix: {new}' in yaml.read_text(encoding='utf-8')
print('Patch complete; restart Harness and test a conversation.')