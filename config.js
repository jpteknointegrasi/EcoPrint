// Supabase connection (project: manna borneo persada).
// URL + publishable key are safe to ship in the browser: every table is closed and all access goes
// through database functions that check prices, stock and admin roles.
// Never put the service_role / secret key here. Leave both empty to run the self-contained demo.
window.NIKEN_CONFIG = {
  supabaseUrl: "https://fhxbtrrehxuwjrlxpnoy.supabase.co",
  supabaseAnonKey: "sb_publishable_4XmZeW1BWV2GEJ83yTkn5w_yhSGv2nN"
};
