import { db } from "./db";
import { signals, type Signal, type InsertSignal } from "@shared/schema";

export interface IStorage {
  getSignals(): Promise<Signal[]>;
  createSignal(signal: InsertSignal): Promise<Signal>;
  clearSignals(): Promise<void>;
}

export class DatabaseStorage implements IStorage {
  async getSignals(): Promise<Signal[]> {
    return await db.select().from(signals).orderBy(signals.timestamp);
  }

  async createSignal(insertSignal: InsertSignal): Promise<Signal> {
    const [signal] = await db.insert(signals).values(insertSignal).returning();
    return signal;
  }

  async clearSignals(): Promise<void> {
    await db.delete(signals);
  }
}

export const storage = new DatabaseStorage();
