import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const signals = pgTable("signals", {
  id: serial("id").primaryKey(),
  asset: text("asset").notNull(),
  action: text("action").notNull(), // CALL or PUT
  strategy: text("strategy").notNull(), // RSI, SMA, Combined
  confidence: integer("confidence").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
  result: text("result"), // WIN, LOSS, or PENDING
  price: text("price"), // Entry price
});

export const insertSignalSchema = createInsertSchema(signals).omit({ 
  id: true, 
  timestamp: true 
});

export type Signal = typeof signals.$inferSelect;
export type InsertSignal = z.infer<typeof insertSignalSchema>;
