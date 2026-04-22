-- Migration: add signal_context column to trades table
-- Run once against trading_db (PostgreSQL port 5433)
-- Safe to run multiple times: uses IF NOT EXISTS check.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'trades'
          AND column_name = 'signal_context'
    ) THEN
        ALTER TABLE trades ADD COLUMN signal_context TEXT;
        RAISE NOTICE 'Column signal_context added to trades.';
    ELSE
        RAISE NOTICE 'Column signal_context already exists. No changes made.';
    END IF;
END;
$$;
