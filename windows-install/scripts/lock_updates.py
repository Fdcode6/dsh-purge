import datetime, pathlib, shutil, sys
MESSAGE = '本地修复版已锁定插件更新：禁止自动升级、在线更新、版本切换和回退。请使用维护后的离线包升级。'
HELPER = """
// LOCAL_REPAIR_UPDATE_LOCK_V1: deliberate immutable policy for this repaired distribution.
function lockedUpdateResult(blocked = false) {
  const version = localVersion();
  return rememberUpdate({
    ok: !blocked, updatesLocked: true, skipped: 'local-repair-update-lock',
    hasUpdate: false, hasBeta: false, applied: false, restartAfter: false,
    needRestart: false, needsFullQuit: false,
    localVersion: version, remoteVersion: '', channel: 'stable', pin: version,
    pinned: true, versions: [{ version, ref: 'local-repair', current: true, latest: true }],
    lanes: {}, error: MESSAGE_LITERAL,
  });
}
""".replace('MESSAGE_LITERAL', __import__('json').dumps(MESSAGE, ensure_ascii=False))
def patch(package):
    target = package / 'lib/update.js'
    text = target.read_text(encoding='utf-8-sig')
    if 'LOCAL_REPAIR_UPDATE_LOCK_V1' in text:
        print('Already locked:', package)
        return
    signatures = [
        ('export async function checkUpdate() {', False),
        ('export async function applyUpdate(jobs = planUpdates(), options = {}) {', True),
        ('async function _applyUpdateImpl(jobs, options) {', True),
        ('export async function switchChannel(channel, { apply = true } = {}) {', True),
        ('export async function switchVersion(ref) {', True),
        ('export async function handleUpdateOp(body = {}) {', True),
        ('export async function autoUpdateIfNeeded() {', False),
    ]
    for signature, blocked in signatures:
        if text.count(signature) != 1: raise RuntimeError('Unknown update implementation: ' + signature)
    for signature, blocked in signatures:
        replacement = signature.replace('jobs = planUpdates()', 'jobs')
        text = text.replace(signature, replacement + '\n  return lockedUpdateResult(' + str(blocked).lower() + ');', 1)
    text += HELPER
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    shutil.copy2(target, str(target) + '.backup-update-lock-' + stamp)
    target.write_text(text, encoding='utf-8')
    print('Updates locked:', package)
if __name__ == '__main__':
    root = pathlib.Path(sys.argv[1]).resolve()
    if len(sys.argv) > 2 and sys.argv[2] == '--package': patch(root)
    else:
        for package in [root / 'plugins/dsh-purge', root / 'profiles/desktop/node_modules/dsh-purge']: patch(package)
