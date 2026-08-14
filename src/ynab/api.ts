import { API, Payee, SaveTransaction as YnabTransaction, TransactionDetail } from "ynab";

const YNAB_BUDGET_ID = process.env.YNAB_BUDGET_ID || "";
const YNAB_API_KEY = process.env.YNAB_API_KEY || "";

const client = new API(YNAB_API_KEY);

export async function createTransaction(transaction: YnabTransaction) {
  transaction.approved = false;

  const resp = await client.transactions.createTransaction(YNAB_BUDGET_ID, { transaction });
  console.log(`YNAB save: ${JSON.stringify(resp)}`);

  if (resp.data.transaction?.transfer_transaction_id) {
    console.log("Clearing other side of transfer");

    const transactionId = resp.data.transaction.transfer_transaction_id;
    const transferTransaction = (await client.transactions.getTransactionById(YNAB_BUDGET_ID, transactionId)).data.transaction;

    transferTransaction.cleared = TransactionDetail.ClearedEnum.Uncleared;

    const transferResp = await client.transactions.updateTransaction(YNAB_BUDGET_ID, transactionId, {
      transaction: {
        id: transferTransaction.id,
        account_id: transferTransaction.account_id,
        date: transferTransaction.date,
        amount: transferTransaction.amount,
        cleared: transferTransaction.cleared,
        approved: false,
      },
    });

    console.log(`YNAB save: ${JSON.stringify(transferResp)}`);
  }
}

export async function updateTransaction(transaction: YnabTransaction): Promise<boolean> {
  transaction.approved = false;

  if (!transaction.import_id) {
    throw new Error("updateTransaction requires import_id");
  }

  const searchFromDate = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30);
  const searchFromDateIso = searchFromDate.toISOString().slice(0, 10);

  const transactions = await client.transactions.getTransactions(YNAB_BUDGET_ID, searchFromDateIso);
  const existingTransaction = transactions.data.transactions.find((t) => t.import_id === transaction.import_id);

  if (!existingTransaction) {
    console.log("Could not find existing transaction");
    return false;
  }

  const resp = await client.transactions.updateTransaction(YNAB_BUDGET_ID, existingTransaction.id, {
    transaction: {
      id: existingTransaction.id,
      account_id: existingTransaction.account_id,
      date: existingTransaction.date,
      amount: existingTransaction.amount,
      cleared: transaction.cleared ?? existingTransaction.cleared,
      approved: false,
    },
  });

  console.log(`YNAB update: ${JSON.stringify(resp)}`);
  return true;
}

export async function deleteTransaction(importId: string) {
  const searchFromDate = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30);
  const searchFromDateIso = searchFromDate.toISOString().slice(0, 10);

  const transactions = await client.transactions.getTransactions(YNAB_BUDGET_ID, searchFromDateIso);
  const existingTransaction = transactions.data.transactions.find((t) => t.import_id === importId);

  if (!existingTransaction) {
    console.log("Could not find existing transaction, ignoring");
    return;
  }

  console.log(`Would delete transaction (if YNAB had a delete endpoint): ${JSON.stringify(existingTransaction)}`);
}

export async function getPayees(): Promise<Array<Payee>> {
  const payees = (await client.payees.getPayees(YNAB_BUDGET_ID)).data.payees;
  console.log(`Payees: ${JSON.stringify(payees)}`);
  return payees;
}