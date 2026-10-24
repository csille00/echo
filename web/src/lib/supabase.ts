import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL ?? "http://localhost";
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? "unused";

/** Only used when VITE_AUTH_MODE=supabase */
export const supabase = createClient(url, anonKey);
