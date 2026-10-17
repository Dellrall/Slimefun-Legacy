package io.github.thebusybiscuit.slimefun4.core.commands.subcommands;

import io.github.bakedlibs.dough.common.CommonPatterns;
import io.github.bakedlibs.dough.items.CustomItemStack;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItem;
import io.github.thebusybiscuit.slimefun4.core.commands.SlimefunCommand;
import io.github.thebusybiscuit.slimefun4.core.commands.SubCommand;
import io.github.thebusybiscuit.slimefun4.core.multiblocks.MultiBlockMachine;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import io.github.thebusybiscuit.slimefun4.implementation.items.weapons.CowHearder;
import java.util.Locale;
import java.util.Map;
import javax.annotation.ParametersAreNonnullByDefault;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

class GiveCommand extends SubCommand {

    private static final String PLACEHOLDER_PLAYER = "%player%";
    private static final String PLACEHOLDER_ITEM = "%item%";
    private static final String PLACEHOLDER_AMOUNT = "%amount%";

    @ParametersAreNonnullByDefault
    GiveCommand(Slimefun plugin, SlimefunCommand cmd) {
        super(plugin, cmd, "give", false);
    }

    @Override
    public void onExecute(CommandSender sender, String[] args) {
        if (args.length == 2 && CowHearder.ID.equalsIgnoreCase(args[1])) {
            giveCowHearderToSelf(sender);
            return;
        }

        if (sender.hasPermission("slimefun.cheat.items") || !(sender instanceof Player)) {
            if (args.length > 2) {
                Player p = Bukkit.getPlayerExact(args[1]);

                if (p != null) {
                    SlimefunItem sfItem = SlimefunItem.getById(args[2].toUpperCase(Locale.ROOT));

                    if (sfItem != null) {
                        if (CowHearder.ID.equals(sfItem.getId())) {
                            boolean senderIsAdmin = sender instanceof ConsoleCommandSender
                                    || (sender instanceof Player player && player.isOp());
                            int amount = args.length == 4 ? parseAmount(args) : 1;
                            if (args.length > 4 || !CowHearder.mayGive(senderIsAdmin, p.isOp(), amount)) {
                                sender.sendMessage(Component.text(
                                        "The Cow Hearder may only be given by an operator or console to an OP player"
                                                + " (one at a time).",
                                        NamedTextColor.RED));
                                return;
                            }
                        }

                        giveItem(sender, p, sfItem, args);
                    } else {
                        Slimefun.getLocalization()
                                .sendMessage(
                                        sender,
                                        "messages.invalid-item",
                                        true,
                                        msg -> msg.replace(PLACEHOLDER_ITEM, args[2]));
                    }
                } else {
                    Slimefun.getLocalization()
                            .sendMessage(
                                    sender,
                                    "messages.not-online",
                                    true,
                                    msg -> msg.replace(PLACEHOLDER_PLAYER, args[1]));
                }
            } else {
                Slimefun.getLocalization()
                        .sendMessage(
                                sender,
                                "messages.usage",
                                true,
                                msg -> msg.replace("%usage%", "/sf give <Player> <Slimefun Item> [Amount]"));
            }
        } else {
            Slimefun.getLocalization().sendMessage(sender, "messages.no-permission", true);
        }
    }

    private void giveCowHearderToSelf(CommandSender sender) {
        if (!(sender instanceof Player player) || !player.isOp()) {
            Slimefun.getLocalization().sendMessage(sender, "messages.no-permission", true);
            return;
        }

        SlimefunItem sword = SlimefunItem.getById(CowHearder.ID);
        if (sword == null) {
            player.sendMessage(Component.text("The Cow Hearder is not registered.", NamedTextColor.RED));
            return;
        }

        if (player.getInventory().addItem(new CustomItemStack(sword.getItem(), 1)).isEmpty()) {
            player.sendMessage(Component.text("The Cow Hearder has been added to your inventory.", NamedTextColor.GREEN));
        } else {
            player.sendMessage(Component.text("Your inventory is full.", NamedTextColor.RED));
        }
    }

    private void giveItem(CommandSender sender, Player p, SlimefunItem sfItem, String[] args) {
        if (sfItem instanceof MultiBlockMachine) {
            Slimefun.getLocalization().sendMessage(sender, "guide.cheat.no-multiblocks");
        } else {
            int amount = parseAmount(args);

            if (amount > 0) {
                Slimefun.getLocalization()
                        .sendMessage(
                                p,
                                "messages.given-item",
                                true,
                                msg -> msg.replace(PLACEHOLDER_ITEM, sfItem.getItemName())
                                        .replace(PLACEHOLDER_AMOUNT, String.valueOf(amount)));
                Map<Integer, ItemStack> excess =
                        p.getInventory().addItem(new CustomItemStack(sfItem.getItem(), amount));
                if (Slimefun.getCfg().getBoolean("options.drop-excess-sf-give-items") && !excess.isEmpty()) {
                    for (ItemStack is : excess.values()) {
                        p.getWorld().dropItem(p.getLocation(), is);
                    }
                }

                Slimefun.getLocalization()
                        .sendMessage(
                                sender,
                                "messages.give-item",
                                true,
                                msg -> msg.replace(PLACEHOLDER_PLAYER, args[1])
                                        .replace(PLACEHOLDER_ITEM, sfItem.getItemName())
                                        .replace(PLACEHOLDER_AMOUNT, String.valueOf(amount)));
            } else {
                Slimefun.getLocalization()
                        .sendMessage(
                                sender,
                                "messages.invalid-amount",
                                true,
                                msg -> msg.replace(PLACEHOLDER_AMOUNT, args[3]));
            }
        }
    }

    private int parseAmount(String[] args) {
        int amount = 1;

        if (args.length == 4) {
            if (CommonPatterns.NUMERIC.matcher(args[3]).matches()) {
                try {
                    amount = Integer.parseInt(args[3]);
                } catch (NumberFormatException ignored) {
                    return 0;
                }
            } else {
                return 0;
            }
        }

        return amount;
    }
}
