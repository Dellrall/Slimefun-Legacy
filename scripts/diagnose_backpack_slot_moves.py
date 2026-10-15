#!/usr/bin/env python3
"""Generate isolated desired-invariant tests; never modify production source.

Run only against reviewed source 5a9d83f42f6dffc65958f09ffab6a4c4247afd3d.
The baseline is not assumed crash-atomic: conservation failures are evidence,
not a reason to weaken the desired invariant or to merge these diagnostics.
"""
from pathlib import Path

ROOT = Path('src/test/java/com/xzavier0722/mc/plugin/slimefun4/storage/controller')


def replace_once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError(f'Expected one exact fixture anchor: {before[:80]!r}')
    return text.replace(before, after, 1)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('Fixture section identity changed')
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement + '\n\n' + text[b:]


def main() -> None:
    probe = (ROOT / 'BackpackProcessProbe.java').read_text()
    test = (ROOT / 'BackpackProcessRestartTest.java').read_text()
    for old, new in [('BackpackProcessRestartTest', 'BackpackMoveCrashTest'),
                     ('BackpackProcessProbe', 'BackpackMoveCrashProbe')]:
        probe = probe.replace(old, new)
        test = test.replace(old, new)
    probe = probe.replace('BACKPACK_PROCESS:', 'BACKPACK_MOVE_PROCESS:')
    test = test.replace('BACKPACK_PROCESS:', 'BACKPACK_MOVE_PROCESS:')
    test = replace_once(test,
        '        AFTER_WRITE_BEFORE_ACK(74),\n        AFTER_ACK(75);',
        '        AFTER_INSERT_BEFORE_DELETE(74),\n        AFTER_DELETE_BEFORE_INSERT(76),\n        AFTER_ACK(75);')
    test = test.replace('freshProcessReadsTheExpectedCommittedStateWithoutRewritingOtherRows',
                        'interruptedSlotMoveMustNotCreateOrLoseItems')
    probe = replace_once(probe, 'pack.getInventory().setItem(0, item(7));',
        'pack.getInventory().setItem(1, pack.getInventory().getItem(8).clone());\n'
        '            pack.getInventory().setItem(8, null);')
    probe = replace_once(probe, 'case BEFORE_WRITE, AFTER_WRITE_BEFORE_ACK -> {',
        'case BEFORE_WRITE, AFTER_INSERT_BEFORE_DELETE, AFTER_DELETE_BEFORE_INSERT -> {')
    probe = replace_once(probe,
        '                    assertEquals(1, adapter.writes.get());\n'
        '                    assertEquals(0, adapter.deletes.get());\n'
        '                }\n                case AFTER_ACK, CLEAN_SHUTDOWN -> {',
        '                }\n                case AFTER_ACK, CLEAN_SHUTDOWN -> {')
    probe = replace_once(probe,
        '                    assertEquals(0, adapter.deletes.get());\n'
        '                    assertTrue(pack.getSnapshot()',
        '                    assertEquals(1, adapter.deletes.get());\n'
        '                    assertTrue(pack.getSnapshot()')
    probe = replace_section(probe,
        '        private void verify(Path directory,',
        '        private PlayerBackpack load(',
        '''        private void verify(Path directory, BackpackMoveCrashTest.Boundary boundary) throws Exception {
            Properties seed = new Properties();
            try (var stream = Files.newInputStream(directory.resolve("seed-rows.properties"))) {
                seed.load(stream);
            }
            Map<String, String> beforeRead = rows();
            // Check every unaffected row before testing the intentionally stronger invariant.
            for (String key : seed.stringPropertyNames()) {
                if (!key.equals(TARGET + ":8")) {
                    assertEquals(seed.getProperty(key), beforeRead.get(key), "Untouched row " + key);
                }
            }
            PlayerBackpack healthy = load(HEALTHY, 2);
            assertContents(healthy, 23);
            PlayerBackpack target = load(TARGET, 1);
            int total = 0;
            for (int slot = 0; slot < 9; slot++) {
                ItemStack actual = target.getInventory().getItem(slot);
                if (actual != null && !actual.isEmpty()) {
                    assertEquals(item(23).getType(), actual.getType());
                    assertEquals(item(23).getItemMeta(), actual.getItemMeta());
                    total += actual.getAmount();
                    System.out.println("MOVE_SLOT:" + boundary + ":" + slot + ":" + actual.getAmount());
                }
            }
            System.out.println("MOVE_TOTAL:" + boundary + ":" + total + ":expected=46");
            System.out.flush();
            assertEquals(46, total, "A same-backpack slot move must conserve items across a process interruption");
            int expectedMovedSlot = switch (boundary) {
                case BEFORE_WRITE -> 8;
                case AFTER_ACK, CLEAN_SHUTDOWN -> 1;
                case AFTER_INSERT_BEFORE_DELETE, AFTER_DELETE_BEFORE_INSERT ->
                    target.getInventory().getItem(1) == null ? 8 : 1;
            };
            for (int slot = 0; slot < 9; slot++) {
                ItemStack actual = target.getInventory().getItem(slot);
                if (slot == 0 || slot == expectedMovedSlot) {
                    assertNotNull(actual);
                    assertEquals(item(23), actual);
                } else {
                    assertNull(actual);
                }
            }
            controller.saveBackpackInventoryAsync(target).get(WAIT_SECONDS, TimeUnit.SECONDS);
            controller.saveBackpackInventoryAsync(healthy).get(WAIT_SECONDS, TimeUnit.SECONDS);
            assertEquals(0, adapter.writes.get());
            assertEquals(0, adapter.deletes.get());
            assertEquals(beforeRead, rows());
        }''')
    probe = replace_section(probe,
        '        @Override\n        public void setData(RecordKey key, RecordSet data)',
        '        private void block()',
        '''        @Override
        public void setData(RecordKey key, RecordSet data) {
            writes.incrementAndGet();
            if (boundary == BackpackMoveCrashTest.Boundary.BEFORE_WRITE) {
                block();
            }
            if (boundary == BackpackMoveCrashTest.Boundary.AFTER_DELETE_BEFORE_INSERT) {
                awaitRelease();
            }
            super.setData(key, data);
            if (boundary == BackpackMoveCrashTest.Boundary.AFTER_INSERT_BEFORE_DELETE) {
                block();
            }
        }

        @Override
        public void deleteData(RecordKey key) {
            deletes.incrementAndGet();
            if (boundary == BackpackMoveCrashTest.Boundary.BEFORE_WRITE) {
                block();
            }
            if (boundary == BackpackMoveCrashTest.Boundary.AFTER_INSERT_BEFORE_DELETE) {
                awaitRelease();
            }
            super.deleteData(key);
            if (boundary == BackpackMoveCrashTest.Boundary.AFTER_DELETE_BEFORE_INSERT) {
                block();
            }
        }''')
    probe = replace_once(probe,
        '        private void block() {\n            entered.countDown();\n            try {',
        '        private void block() {\n            entered.countDown();\n            awaitRelease();\n'
        '        }\n\n        private void awaitRelease() {\n            try {')
    # Successful child output is also retained in the XML, not only failed-child output.
    test = replace_once(test, '            String output = readLog(log);',
        '            String output = readLog(log);\n'
        '            System.out.println("MOVE_CHILD_LOG:" + boundary + ":" + phase + "\\n" + output);')
    for name, text in [('BackpackMoveCrashProbe.java', probe), ('BackpackMoveCrashTest.java', test)]:
        path = ROOT / name
        if path.exists():
            raise FileExistsError(path)
        path.write_text(text)
    print('Created two diagnostic test sources; production source and original tests are unchanged.')


if __name__ == '__main__':
    main()
