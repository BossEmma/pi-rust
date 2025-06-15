use reqwest::blocking::Client;
use serde::Deserialize;
use std::collections::HashMap;
use std::fs::File;
use std::io::BufReader;
use std::error::Error;
use regex::Regex;
use std::thread;
use std::time::Duration;

#[derive(Deserialize, Debug)]
struct SubmitResponse {
    hash: Option<String>,
    result_xdr: Option<String>,
    extras: Option<Extras>,
}

#[derive(Deserialize, Debug)]
struct Extras {
    result_codes: Option<ResultCodes>,
}

#[derive(Deserialize, Debug)]
struct ResultCodes {
    transaction: Option<String>,
}

fn main() -> Result<(), Box<dyn Error>> {
    let file = File::open("xdrs.json")?;
    let reader = BufReader::new(file);

    let tx_map: HashMap<String, String> = serde_json::from_reader(reader)?;

    let re = Regex::new(r"transaction(\d+)")?;
    let mut ordered_keys: Vec<_> = tx_map.keys().collect();
    ordered_keys.sort_by_key(|k| {
        re.captures(k)
            .and_then(|cap| cap.get(1))
            .and_then(|m| m.as_str().parse::<u32>().ok())
            .unwrap_or(0)
    });

    let client = Client::new();
    let horizon_url = "https://api.mainnet.minepi.com/transactions";

    for key in ordered_keys {
        if let Some(xdr) = tx_map.get(key) {
            println!("📤 Submitting {}...", key);

            let mut attempts = 0;
            let max_retries = 3;
            let mut success = false;

            while attempts < max_retries {
                let res = client
                    .post(horizon_url)
                    .form(&[("tx", xdr)])
                    .send();

                match res {
                    Ok(response) => {
                        if response.status().is_success() {
                            let parsed: SubmitResponse = response.json()?;
                            println!("✅ Submitted: {}", key);
                            println!("    Hash: {:?}", parsed.hash);
                            success = true;
                            break;
                        } else {
                            let parsed: SubmitResponse = response.json()?;
                            println!("❌ Failed to submit: {}", key);
                            if let Some(extras) = parsed.extras {
                                if let Some(codes) = extras.result_codes {
                                    println!("    Error Code: {:?}", codes.transaction);
                                }
                            } else {
                                println!("    Full response: {:?}", parsed);
                            }
                        }
                    }
                    Err(e) => {
                        println!("⚠️ Request error: {}. Retrying...", e);
                    }
                }

                attempts += 1;
            }

            if !success {
                println!("❌ All retries failed for {}", key);
            }
            
            thread::sleep(Duration::from_millis(200));
        }
    }

    Ok(())
}
