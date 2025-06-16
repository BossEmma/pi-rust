use reqwest::blocking::Client;
use serde::Deserialize;
use std::error::Error;
use std::fs;
use std::thread;
use std::time::Duration;
use std::collections::BTreeMap;
use glob::glob;

#[derive(Deserialize)]
struct SubmitResponse {
    hash: Option<String>,
    extras: Option<Extras>,
}

#[derive(Deserialize)]
struct Extras {
    result_codes: Option<ResultCodes>,
}

#[derive(Deserialize)]
struct ResultCodes {
    transaction: Option<String>,
}

fn submit_xdr(filename: &str, tx_name: &str, xdr: &str, client: &Client) {
    println!("{}: Submitting {}...", filename, tx_name);
    match client
        .post("http://173.230.130.166:8000/transactions")
        .form(&[("tx", xdr)])
        .send()
    {
        Ok(response) if response.status().is_success() => {
            if let Ok(parsed) = response.json::<SubmitResponse>() {
                println!("✅ Submitted! {}: {}", filename, tx_name);
                if let Some(hash) = parsed.hash {
                    println!("    Hash: {}", hash);
                }
            } else {
                println!("✅ Submitted! {}: {}", filename, tx_name);
            }
        }
        Ok(response) => {
            println!("❌ Failed (HTTP {}). {}: {}", response.status().as_u16(), filename, tx_name);
            if let Ok(parsed) = response.json::<SubmitResponse>() {
                if let Some(tx_code) = parsed.extras
                    .and_then(|e| e.result_codes)
                    .and_then(|r| r.transaction) {
                    println!("    Error: {}", tx_code);
                }
            }
        }
        Err(e) => println!("⚠️ Error: {}. {}: {}", e, filename, tx_name),
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    // Find all xdrs*.json files in current directory
    let pattern = "xdrs*.json";
    let mut file_maps = Vec::new();
    let mut filenames = Vec::new();

    for entry in glob(pattern)? {
        let path = entry?;
        let filename = path.file_name().unwrap().to_string_lossy().to_string();
        let file_content = fs::read_to_string(&path)?;
        let xdr_map: BTreeMap<String, String> = serde_json::from_str(&file_content)?;
        file_maps.push(xdr_map);
        filenames.push(filename);
    }

    // Assume all files have the same transaction keys (transaction1..transaction100)
    for tx_idx in 1..=100 {
        let tx_name = format!("transaction{}", tx_idx);
        let mut handles = vec![];

        for (file_idx, xdr_map) in file_maps.iter().enumerate() {
            if let Some(xdr) = xdr_map.get(&tx_name) {
                let filename = filenames[file_idx].clone();
                let xdr = xdr.clone();
                let tx_name = tx_name.clone();
                let handle = thread::spawn(move || {
                    let client = Client::builder()
                        .timeout(Duration::from_secs(10))
                        .tcp_nodelay(true)
                        .build()
                        .expect("Failed to build client");
                    submit_xdr(&filename, &tx_name, &xdr, &client);
                    thread::sleep(Duration::from_millis(500)); // 0.1 second delay after each submission
                });
                handles.push(handle);
            }
        }

        // Wait for all threads for this transaction index to finish before moving to the next
        for handle in handles {
            handle.join().expect("Thread panicked");
        }
    }

    println!("All XDRs submitted.");
    Ok(())
}
