import { db } from "./db";
import { signals, type Signal, type InsertSignal, botLogs, type BotLog, type InsertBotLog } from "@shared/schema";
import { desc } from "drizzle-orm";

export interface IStorage {
  getSignals(): Promise<Signal[]>;
  createSignal(signal: InsertSignal): Promise<Signal>;
  clearSignals(): Promise<void>;
  getLogs(): Promise<BotLog[]>;
  createLog(log: InsertBotLog): Promise<BotLog>;
}

export class DatabaseStorage implements IStorage {
  async getSignals(): Promise<Signal[]> {
    return await db.select().from(signals).orderBy(desc(signals.timestamp));
  }

  async createSignal(insertSignal: InsertSignal): Promise<Signal> {
    const [signal] = await db.insert(signals).values(insertSignal).returning();
    return signal;
  }

  async clearSignals(): Promise<void> {
    await db.delete(signals);
  }

  async getLogs(): Promise<BotLog[]> {
    return await db.select().from(botLogs).orderBy(desc(botLogs.timestamp)).limit(50);
  }

  async createLog(insertLog: InsertBotLog): Promise<BotLog> {
    const [log] = await db.insert(botLogs).values(insertLog).returning();
    return log;
  }
}

export const storage = new DatabaseStorage();
