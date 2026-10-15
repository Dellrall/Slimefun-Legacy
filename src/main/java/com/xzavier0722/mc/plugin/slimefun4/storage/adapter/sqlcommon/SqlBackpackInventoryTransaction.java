package com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon;

import com.xzavier0722.mc.plugin.slimefun4.storage.common.BackpackInventoryBatch;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Locale;
import java.util.Objects;

/** One connection and one commit for one backpack's changed slots; no schema or item-format changes. */
final class SqlBackpackInventoryTransaction {
    private SqlBackpackInventoryTransaction() {}

    static void execute(Connection connection, String prefix, BackpackInventoryBatch batch) throws SQLException {
        Objects.requireNonNull(batch, "batch");
        if (prefix == null || !prefix.matches("[A-Za-z0-9_]*")) {
            throw new IllegalArgumentException("Unsafe or unsupported SQL table prefix for backpack saves");
        }
        if (batch.slots().isEmpty()) {
            return;
        }
        if (!connection.getAutoCommit()) {
            throw new SQLException("Backpack save requires its own transaction, not a caller-owned transaction");
        }
        if (!connection.getMetaData().supportsTransactions()) {
            throw new SQLException("Storage does not support atomic backpack saves");
        }
        String table = prefix + "backpack_inventory";
        String product = connection.getMetaData().getDatabaseProductName().toLowerCase(Locale.ROOT);
        boolean mysql = product.equals("mysql") || product.equals("mariadb");
        if (mysql) {
            requireInnoDb(connection, table);
        } else if (!product.equals("sqlite") && !product.equals("postgresql")) {
            throw new SQLException("No atomic backpack save contract is defined for this database");
        }
        boolean beginAttempted = false;
        boolean resolved = false;
        boolean commitAttempted = false;
        Throwable failure = null;
        try {
            beginAttempted = true;
            connection.setAutoCommit(false);
            writeSlots(connection, table, mysql, batch);
            commitAttempted = true;
            connection.commit();
            resolved = true;
        } catch (SQLException | RuntimeException | Error cause) {
            if (beginAttempted) {
                try {
                    connection.rollback();
                    resolved = true;
                } catch (SQLException | RuntimeException | Error rollbackFailure) {
                    cause.addSuppressed(rollbackFailure);
                    abort(connection, cause);
                }
            }
            if (cause instanceof Error error) {
                failure = error;
                throw error;
            }
            var rejected = new IllegalStateException(
                    "Backpack save did not confirm commit for " + batch.backpackId()
                            + (commitAttempted ? "; commit outcome may be uncertain" : "; transaction failed"),
                    cause);
            failure = rejected;
            throw rejected;
        } finally {
            // Changing auto-commit to true can COMMIT. Never do so after an unresolved rollback.
            if (beginAttempted && resolved) {
                try {
                    connection.setAutoCommit(true);
                } catch (SQLException | RuntimeException resetFailure) {
                    abort(connection, resetFailure);
                    if (failure != null) {
                        failure.addSuppressed(resetFailure);
                    } else {
                        throw new IllegalStateException(
                                "Backpack commit completed but connection cleanup failed; save remains unacknowledged",
                                resetFailure);
                    }
                }
            }
        }
    }

    private static void writeSlots(Connection connection, String table, boolean mysql, BackpackInventoryBatch batch)
            throws SQLException {
        String upsert = "INSERT INTO " + table + " (b_id, i_slot, i_item) VALUES (?, ?, ?)"
                + (mysql
                        ? " ON DUPLICATE KEY UPDATE i_item = ?"
                        : " ON CONFLICT (b_id, i_slot) DO UPDATE SET i_item = excluded.i_item");
        try (var put = connection.prepareStatement(upsert);
                var remove = connection.prepareStatement("DELETE FROM " + table + " WHERE b_id = ? AND i_slot = ?")) {
            for (BackpackInventoryBatch.Slot slot : batch.slots()) {
                byte[] payload = slot.payload();
                var statement = payload == null ? remove : put;
                statement.setString(1, batch.backpackId());
                statement.setInt(2, slot.index());
                if (payload != null) {
                    statement.setBytes(3, payload);
                    if (mysql) {
                        statement.setBytes(4, payload);
                    }
                }
                int affected = statement.executeUpdate();
                // MySQL may report 0 for an identical value and 2 for a changed upsert.
                if (payload == null
                        ? affected < 0 || affected > 1
                        : mysql ? affected < 0 || affected > 2 : affected != 1) {
                    throw new SQLException("Backpack save affected an unexpected number of rows");
                }
            }
        }
    }

    private static void requireInnoDb(Connection connection, String table) throws SQLException {
        try (var statement = connection.prepareStatement(
                "SELECT engine FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = ?")) {
            statement.setString(1, table);
            try (var rows = statement.executeQuery()) {
                if (!rows.next() || !"InnoDB".equalsIgnoreCase(rows.getString(1)) || rows.next()) {
                    throw new SQLException("Atomic backpack saves require a verified InnoDB inventory table");
                }
            }
        }
    }

    private static void abort(Connection connection, Throwable failure) {
        try {
            connection.abort(Runnable::run);
        } catch (SQLException | RuntimeException | Error abortFailure) {
            failure.addSuppressed(abortFailure);
        }
    }
}
