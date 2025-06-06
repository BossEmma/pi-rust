use reqwest::Client;
use std::{collections::HashMap, fs};
use futures::future::join_all;

const BATCH_SIZE: usize = 25;
const API_URL: &str = "http://127.0.0.1:8000/transactions";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Load and parse the XDRs
    let file = fs::read_to_string("xdrs.json")?;
    let xdrs: HashMap<String, String> = serde_json::from_str(&file)?;

    // Sort by the numeric part of the "transactionX" key
    let mut entries: Vec<_> = xdrs.into_iter().collect();
    entries.sort_by_key(|(k, _)| {
        k.trim_start_matches("transaction")
            .parse::<u32>()
            .unwrap_or(0)
    });

    let client = Client::new();

    for (i, chunk) in entries.chunks(BATCH_SIZE).enumerate() {
        let start_label = &chunk.first().unwrap().0;
        let end_label = &chunk.last().unwrap().0;
        println!("\n📦 Sending batch {}: {} - {}", i + 1, start_label, end_label);

        // Submit all transactions in parallel
        let tasks = chunk.iter().map(|(label, xdr)| {
            let client = client.clone();
            let label = label.clone();
            let xdr = xdr.clone();
            tokio::spawn(async move {
                submit_transaction(&client, xdr, label).await;
            })
        });

        // Wait for all tasks to finish
        let _ = join_all(tasks).await;

        println!("✅ Batch {} submitted.\n", i + 1);
    }

    Ok(())
}

async fn submit_transaction(client: &Client, xdr: String, label: String) {
    let form = [("tx", xdr)];

    match client.post(API_URL).form(&form).send().await {
        Ok(response) => {
            if response.status().is_success() {
                println!("✅ {}: Submitted successfully", label);
            } else {
                let status = response.status();
                let text = response.text().await.unwrap_or_else(|_| "Unknown error".into());
                println!("❌ {}: HTTP {} → {}", label, status, text);
            }
        }
        Err(e) => {
            println!("❌ {}: Request failed → {}", label, e);
        }
    }
}
