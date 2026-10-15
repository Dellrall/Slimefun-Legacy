package com.xzavier0722.mc.plugin.slimefun4.storage.controller;

import com.xzavier0722.mc.plugin.slimefun4.storage.common.BackpackInventoryBatch;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.DataScope;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.FieldKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordSet;
import java.util.ArrayList;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiFunction;

/** Adapts immutable batches to existing recording fixtures, not a production or durable writer. */
final class BackpackBatchRecording {
    private BackpackBatchRecording() {}

    static CompletableFuture<Void> capture(
            BackpackInventoryBatch batch, BiFunction<RecordKey, RecordSet, CompletableFuture<Void>> recorder) {
        var completions = new ArrayList<CompletableFuture<Void>>();
        for (var slot : batch.slots()) {
            var key = new RecordKey(DataScope.BACKPACK_INVENTORY);
            key.addCondition(FieldKey.BACKPACK_ID, batch.backpackId());
            key.addCondition(FieldKey.INVENTORY_SLOT, Integer.toString(slot.index()));
            key.addField(FieldKey.INVENTORY_ITEM);
            RecordSet record = null;
            if (slot.payload() != null) {
                record = new RecordSet();
                record.put(FieldKey.BACKPACK_ID, batch.backpackId());
                record.put(FieldKey.INVENTORY_SLOT, Integer.toString(slot.index()));
                record.put(FieldKey.INVENTORY_ITEM, slot.payload());
            }
            completions.add(recorder.apply(key, record));
        }
        return CompletableFuture.allOf(completions.toArray(CompletableFuture[]::new));
    }
}
