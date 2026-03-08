import { createClient } from "@supabase/supabase-js";

const SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3JnanBtZGpldnVuaG5zam51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDcxODg3MywiZXhwIjoyMDc2Mjk0ODczfQ.tc0AjvByyN3A1iOGwKkOxJh8NNj1ux-G-HhT218fBk8";
const URL = "https://lmcrgjpmdjevunhnsjnu.supabase.co";

const client = createClient(URL, SERVICE_KEY);

async function run() {
  // Test insert with new schema
  console.log("Testing new schema...");
  const testRow = {
    pdf_hash: "__test__",
    pdf_path: "test.pdf",
    top_left_lng: 0,
    top_left_lat: 0,
    top_right_lng: 0,
    top_right_lat: 0,
    bottom_right_lng: 0,
    bottom_right_lat: 0,
    bottom_left_lng: 0,
    bottom_left_lat: 0,
    clip_rect: { x: 10, y: 20, width: 100, height: 200 },
    page_number: 1,
    clipped_image_url: "https://example.com/test.png",
  };

  const { error: insertErr } = await client.from("labels").insert(testRow);
  if (insertErr) {
    console.log("FAIL:", insertErr.message);
    return;
  }

  // Read it back
  const { data, error: readErr } = await client
    .from("labels")
    .select("*")
    .eq("pdf_hash", "__test__")
    .single();

  if (readErr) {
    console.log("Read error:", readErr.message);
  } else {
    console.log("OK - Row with new columns:");
    console.log("  clip_rect:", JSON.stringify(data.clip_rect));
    console.log("  page_number:", data.page_number);
    console.log("  clipped_image_url:", data.clipped_image_url);
  }

  // Clean up
  await client.from("labels").delete().eq("pdf_hash", "__test__");
  console.log("Cleaned up test row");

  // Verify storage bucket
  const { data: buckets } = await client.storage.listBuckets();
  console.log("\nStorage buckets:", buckets?.map((b) => `${b.name} (public: ${b.public})`));
}

run().catch(console.error);
