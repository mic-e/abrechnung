// transaction handling
import { atomFamily, selectorFamily } from "recoil";
import { groupAccounts } from "./groups";
import { fetchTransactions } from "../api";
import { ws } from "../websocket";
import { userData } from "./auth";
import { DateTime } from "luxon";

export const groupTransactions = atomFamily({
    key: "groupTransactions",
    default: selectorFamily({
        key: "groupTransactions/default",
        get: groupID => async ({ get }) => {
            return await fetchTransactions({ groupID: groupID });
        }
    }),
    effects_UNSTABLE: groupID => [
        ({ setSelf, trigger }) => {
            ws.subscribe("transaction", groupID, ({ subscription_type, transaction_id, element_id }) => {
                if (subscription_type === "transaction" && element_id === groupID) {
                    fetchTransactions({ groupID: element_id }).then(result => {
                        setSelf(result);
                    });
                }
            });
            // TODO: handle registration errors

            return () => {
                ws.unsubscribe("transaction", groupID);
            };
        }
    ]
});

export const transactionsSeenByUser = selectorFamily({
    key: "transacitonsSeenByUser",
    get: groupID => async ({ get }) => {
        const user = get(userData);
        const transactions = get(groupTransactions(groupID));

        return transactions
            .filter(transaction => {
                if (transaction.current_state && transaction.current_state.deleted) {
                    return false;
                }
                if (transaction.pending_changes.hasOwnProperty(user.id)) {
                    return true;
                } else if (transaction.current_state === null) {
                    return false;
                }
                return true;
            })
            .map(transaction => {
                if (transaction.pending_changes.hasOwnProperty(user.id)) {
                    return {
                        id: transaction.id,
                        type: transaction.type,
                        ...transaction.pending_changes[user.id],
                        is_wip: true,
                        has_committed_changes: transaction.current_state != null
                    };
                } else {
                    return {
                        id: transaction.id,
                        type: transaction.type,
                        ...transaction.current_state,
                        is_wip: false,
                        has_committed_changes: true
                    };
                }

            })
            .map(transaction => {
                let transactionAccountBalances = {};
                let remainingTransactionValue = transaction.value;
                if (transaction.purchase_items != null && transaction.purchase_items.length > 0) {
                    for (const purchaseItem of transaction.purchase_items) {
                        if (purchaseItem.deleted) {
                            continue;
                        }

                        let totalUsages = purchaseItem.communist_shares + Object.values(purchaseItem.usages).reduce((acc, curr) => acc + curr, 0);

                        // bill the respective item usage with each participating account
                        Object.entries(purchaseItem.usages).forEach(([accountID, value]) => {
                            if (transactionAccountBalances.hasOwnProperty(accountID)) {
                                transactionAccountBalances[accountID]["positions"] += totalUsages > 0 ? purchaseItem.price / totalUsages * value : 0;
                            } else {
                                transactionAccountBalances[accountID] = {
                                    positions: totalUsages > 0 ? purchaseItem.price / totalUsages * value : 0,
                                    common_debitors: 0,
                                    common_creditors: 0
                                };
                            }
                        });

                        // calculate the remaining purchase item price to be billed onto the communist shares
                        const commonRemainder = totalUsages > 0 ? purchaseItem.price / totalUsages * purchaseItem.communist_shares : 0;
                        remainingTransactionValue = remainingTransactionValue - purchaseItem.price + commonRemainder;
                    }
                }

                const totalDebitorShares = Object.values(transaction.debitor_shares).reduce((acc, curr) => acc + curr, 0);
                const totalCreditorShares = Object.values(transaction.creditor_shares).reduce((acc, curr) => acc + curr, 0);

                Object.entries(transaction.debitor_shares).forEach(([accountID, value]) => {
                    if (transactionAccountBalances.hasOwnProperty(accountID)) {
                        transactionAccountBalances[accountID]["common_debitors"] += totalDebitorShares > 0 ? remainingTransactionValue / totalDebitorShares * value : 0;
                    } else {
                        transactionAccountBalances[accountID] = {
                            positions: 0,
                            common_creditors: 0,
                            common_debitors: totalDebitorShares > 0 ? remainingTransactionValue / totalDebitorShares * value : 0
                        };
                    }
                });
                Object.entries(transaction.creditor_shares).forEach(([accountID, value]) => {
                    if (transactionAccountBalances.hasOwnProperty(accountID)) {
                        transactionAccountBalances[accountID]["common_creditors"] += totalCreditorShares > 0 ? transaction.value / totalCreditorShares * value : 0;
                    } else {
                        transactionAccountBalances[accountID] = {
                            positions: 0,
                            common_debitors: 0,
                            common_creditors: totalCreditorShares > 0 ? transaction.value / totalCreditorShares * value : 0
                        };
                    }
                });

                return {
                    ...transaction,
                    account_balances: transactionAccountBalances
                };
            })
            .sort((t1, t2) => {
                return t1.billed_at === t2.billed_at
                    ? t1.id < t2.id
                    : DateTime.fromISO(t1.billed_at) < DateTime.fromISO(t2.billed_at);
            });
    }
});

export const transactionById = selectorFamily({
    key: "transactionById",
    get: ({ groupID, transactionID }) => async ({ get }) => {
        const transactions = get(transactionsSeenByUser(groupID));
        return transactions?.find(transaction => transaction.id === transactionID);
    }
});

export const accountBalances = selectorFamily({
    key: "accountBalances",
    get: (groupID) => async ({ get }) => {
        const transactions = get(transactionsSeenByUser(groupID));
        const accounts = get(groupAccounts(groupID));
        let accountBalances = Object.fromEntries(accounts.map(account => [account.id, 0]));
        for (const transaction of transactions) {
            if (transaction.deleted) {
                continue; // ignore deleted transactions
            }
            Object.entries(transaction.account_balances).forEach(([accountID, value]) => {
                accountBalances[accountID] += value.common_creditors - value.positions - value.common_debitors;
            });
        }
        return accountBalances;
    }
});
