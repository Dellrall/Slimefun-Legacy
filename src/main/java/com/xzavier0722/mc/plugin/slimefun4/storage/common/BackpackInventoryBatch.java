package com.xzavier0722.mc.plugin.slimefun4.storage.common;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import javax.annotation.Nullable;

/** An immutable, already serialized changed-slot batch for exactly one backpack. */
public record BackpackInventoryBatch(String backpackId, List<Slot> slots) {
    public BackpackInventoryBatch {
        Objects.requireNonNull(backpackId, "backpackId");
        if (!UUID.fromString(backpackId).toString().equals(backpackId)) {
            throw new IllegalArgumentException("Backpack identity must be a canonical UUID");
        }
        slots = List.copyOf(slots);
        var seen = new HashSet<Integer>();
        for (Slot slot : slots) {
            if (!seen.add(slot.index())) {
                throw new IllegalArgumentException("A backpack slot cannot occur twice in one save");
            }
        }
    }

    /** A null payload deletes only this slot; non-null payloads are never reserialized by the writer. */
    public record Slot(int index, @Nullable byte[] payload) {
        public Slot {
            if (index < 0 || index >= 54) {
                throw new IllegalArgumentException("Backpack slot must be between 0 and 53");
            }
            if (payload != null) {
                if (payload.length == 0) {
                    throw new IllegalArgumentException("An empty payload is not a staged item");
                }
                payload = payload.clone();
            }
        }

        @Override
        public byte[] payload() {
            return payload == null ? null : payload.clone();
        }
    }
}
