import { pgTable, text, serial, integer, boolean, timestamp, decimal } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const signals = pgTable("signals", {
  id: serial("id").primaryKey(),
  asset: text("asset").notNull(),
  action: text("action").notNull(), // CALL or PUT
  strategy: text("strategy").notNull(), // RSI, SMA, MHI, Twin Towers, etc.
  confidence: integer("confidence").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
  result: text("result"), // WIN, LOSS, or PENDING
  price: text("price"), // Entry price
  assetType: text("asset_type").notNull().default("Normal"), // Normal or OTC
  volatility: text("volatility").notNull().default("Média"), // Baixa, Média, Alta
  probability: integer("probability"), // Historical probability %
});

export const insertSignalSchema = createInsertSchema(signals).omit({ 
  id: true, 
  timestamp: true 
});

export type Signal = typeof signals.$inferSelect;
export type InsertSignal = z.infer<typeof insertSignalSchema>;
