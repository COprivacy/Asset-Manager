import { pgTable, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";
import { sql } from "drizzle-orm";

export const signals = pgTable("signals", {
  id: serial("id").primaryKey(),
  asset: text("asset").notNull(),
  action: text("action").notNull(),
  strategy: text("strategy").notNull(),
  confidence: integer("confidence").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
  result: text("result"),
  price: text("price"),
  assetType: text("asset_type").notNull().default("Normal"),
  volatility: text("volatility").notNull().default("Média"),
  probability: integer("probability"),
  reasoning: text("reasoning"), // Added for AI logs
});

export const botLogs = pgTable("bot_logs", {
  id: serial("id").primaryKey(),
  message: text("message").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
});

export const insertSignalSchema = createInsertSchema(signals).omit({ 
  id: true, 
  timestamp: true 
});

export const insertBotLogSchema = createInsertSchema(botLogs).omit({
  id: true,
  timestamp: true
});

export type Signal = typeof signals.$inferSelect;
export type InsertSignal = z.infer<typeof insertSignalSchema>;
export type BotLog = typeof botLogs.$inferSelect;
export type InsertBotLog = z.infer<typeof insertBotLogSchema>;
