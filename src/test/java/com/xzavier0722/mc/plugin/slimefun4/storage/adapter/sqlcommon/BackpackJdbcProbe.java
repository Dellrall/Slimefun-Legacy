package com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon;

import com.zaxxer.hikari.HikariDataSource;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

/** Test-only observation/fault injection around actual JDBC statement and commit boundaries. */
public final class BackpackJdbcProbe {
    public record Operation(String backpackId, int slot, boolean delete) {}

    @FunctionalInterface
    public interface Hook<T> {
        void accept(T value) throws SQLException;
    }

    @FunctionalInterface
    public interface Action {
        void run() throws SQLException;
    }

    public volatile Hook<Operation> before = operation -> {};
    public volatile Hook<Operation> after = operation -> {};
    public volatile Action beforeCommit = () -> {};
    public volatile Action afterCommit = () -> {};

    public HikariDataSource wrapDataSource(HikariDataSource source) {
        return new HikariDataSource() {
            @Override
            public Connection getConnection() throws SQLException {
                return wrap(source.getConnection());
            }

            @Override
            public void evictConnection(Connection connection) {
                source.evictConnection(((ConnectionHandler) Proxy.getInvocationHandler(connection)).connection);
            }

            @Override
            public void close() {
                source.close();
            }
        };
    }

    public Connection wrap(Connection connection) {
        return (Connection) Proxy.newProxyInstance(
                Connection.class.getClassLoader(),
                new Class<?>[] {Connection.class},
                new ConnectionHandler(connection));
    }

    private final class ConnectionHandler implements InvocationHandler {
        private final Connection connection;

        private ConnectionHandler(Connection connection) {
            this.connection = connection;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] arguments) throws Throwable {
            if (method.getName().equals("commit")) {
                beforeCommit.run();
                Object result = call(connection, method, arguments);
                afterCommit.run();
                return result;
            }
            Object result = call(connection, method, arguments);
            if (method.getName().equals("prepareStatement")
                    && arguments[0] instanceof String sql
                    && sql.contains("backpack_inventory ")
                    && (sql.startsWith("INSERT INTO ") || sql.startsWith("DELETE FROM "))) {
                return statement((PreparedStatement) result, sql.startsWith("DELETE FROM "));
            }
            return result;
        }
    }

    private PreparedStatement statement(PreparedStatement statement, boolean delete) {
        Map<Integer, Object> parameters = new HashMap<>();
        return (PreparedStatement) Proxy.newProxyInstance(
                PreparedStatement.class.getClassLoader(),
                new Class<?>[] {PreparedStatement.class},
                (proxy, method, arguments) -> {
                    String name = method.getName();
                    if (name.equals("setString") || name.equals("setInt")) {
                        parameters.put((Integer) arguments[0], arguments[1]);
                    } else if (name.equals("clearParameters")) {
                        parameters.clear();
                    } else if (name.equals("executeUpdate")) {
                        var operation = new Operation((String) parameters.get(1), (Integer) parameters.get(2), delete);
                        before.accept(operation);
                        Object result = call(statement, method, arguments);
                        after.accept(operation);
                        return result;
                    }
                    return call(statement, method, arguments);
                });
    }

    private static Object call(Object target, Method method, Object[] arguments) throws Throwable {
        try {
            return method.invoke(target, arguments);
        } catch (InvocationTargetException failure) {
            throw failure.getCause();
        }
    }
}
