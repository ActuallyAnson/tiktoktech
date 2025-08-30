from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any
import argparse
import json
import ast
import pandas as pd

from dotenv import load_dotenv
import hashlib
import zipfile
from datetime import datetime
from web3 import Web3

IN_ENRICHED_DEFAULT = "outputs/llm_enriched.csv"
IN_AGENT_DEFAULT = "outputs/agent_results.csv"
OUT_FINAL_DEFAULT = "outputs/final_results.csv"

# ----------------- helpers -----------------
def _to_list(v) -> List[str]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            # try JSON first then Python literal
            try:
                val = json.loads(s)
                if isinstance(val, list):
                    return [str(x) for x in val]
            except Exception:
                try:
                    val = ast.literal_eval(s)
                    if isinstance(val, (list, tuple)):
                        return [str(x) for x in val]
                except Exception:
                    inner = s.strip("[]")
                    return [p.strip().strip("'").strip('"') for p in inner.split(",") if p.strip()]
        return [s]
    return []

def collapse_reasoning(agent_rows: pd.DataFrame) -> str:
    """
    Build a short explanation prioritizing ISSUE -> REVIEW -> OK,
    but keeping it crisp (1-2 lines).
    """
    if agent_rows.empty:
        return "No agent decisions available."
    # Prioritize ISSUE, then REVIEW; include agent names for clarity
    parts: List[str] = []
    for label in ("ISSUE", "REVIEW"):
        sub = agent_rows[agent_rows["status"] == label]
        if not sub.empty:
            names = ", ".join(f"{r['agent']}({r.get('score',0):.2f})" for _, r in sub.iterrows())
            parts.append(f"{label}: {names}")
    if not parts:
        parts.append("All assigned agents returned OK.")
    # Add the first non-empty textual reasoning for color (optional)
    for _, r in agent_rows.iterrows():
        rr = str(r.get("reasoning") or "").strip()
        if rr:
            parts.append(rr)
            break
    # Keep it short
    text = " | ".join(parts)
    return (text[:600] + "…") if len(text) > 600 else text

def pick_final_class(agent_rows: pd.DataFrame) -> str:
    if (agent_rows["status"] == "ISSUE").any():
        return "REQUIRED"
    if (agent_rows["status"] == "REVIEW").any():
        return "NEEDS HUMAN REVIEW"
    return "NOT REQUIRED"

def compute_confidence(agent_rows: pd.DataFrame, final_class: str) -> float:
    # scores are 0..1 provided by agents
    if agent_rows.empty:
        return 0.5
    if final_class == "REQUIRED":
        # strongest indicator
        scores = agent_rows.loc[agent_rows["status"] == "ISSUE", "score"].dropna().astype(float)
        return float(scores.max() if not scores.empty else 0.75)
    if final_class == "NEEDS HUMAN REVIEW":
        scores = agent_rows.loc[agent_rows["status"] == "REVIEW", "score"].dropna().astype(float)
        if scores.empty:
            # borderline with no scores recorded
            return 0.6
        return float(scores.mean())
    # NOT REQUIRED
    return 0.9

def hash(filename, algorithm='sha256') -> str:
        """Generate a hash for a file."""
        hash_obj = hashlib.new(algorithm)
        with open(filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

def log_on_chain(hash_value: str) -> str:
        """
        Log the hash value on the Ethereum Sepolia Testnet by 
        sending a self transaction with the hash in the data field
        Args:
            hash_value: The hash value to log
        Return:
            The transaction ID if successful, empty string otherwise
        """
        load_dotenv()
        api_key = os.environ.get('SEPOLIA_API_KEY', '')
        provider = os.environ.get('SEPOLIA_API_PROVIDER', '').lower()
        private_key = os.environ.get('ETH_PRIVATE_KEY', '')

        if api_key == 'your_sepolia_api_key_here' or private_key == 'your_ethereum_private_key_here':
            api_key = ''
            private_key = ''

        if (api_key and provider and private_key):
            match provider:
                case 'alchemy':
                    rpc_url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
                case 'infura':
                    rpc_url = f"https://sepolia.infura.io/v3/{api_key}"
                
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not w3.is_connected():
                print("Failed to connect to Ethereum network, check your API provider and key.\nSupported providers: alchemy, infura")
                return ''

            acct = w3.eth.account.from_key(private_key)
            balance = w3.eth.get_balance(acct.address)
            balance_eth = w3.from_wei(balance, 'ether')

            data_bytes = len(hash_value) // 2  # Each hex pair = 1 byte
            gas_for_data = data_bytes * 16  # 16 gas per non-zero byte (assuming worst case)
            estimated_gas = 21000 + gas_for_data + 1000  # Base + data + buffer

            gas_price = w3.eth.gas_price
            estimated_cost = w3.from_wei(gas_price * estimated_gas, 'ether')
            
            if balance_eth < estimated_cost:
                print(f"Insufficient funds: {balance_eth} ETH (need ~{estimated_cost} ETH)")
                return False

            tx = {
                "to": acct.address,  # Self-send to embed data
                "value": 0,          
                "gas": estimated_gas,        
                "gasPrice": gas_price,
                "nonce": w3.eth.get_transaction_count(acct.address),
                "data": "0x" + hash_value  # Embed hash in transaction data
            }

            try:
                estimated_gas_web3 = w3.eth.estimate_gas(tx)
                tx["gas"] = estimated_gas_web3
                
                signed = acct.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                tx_hash_str = f"0x{tx_hash.hex()}"
                print(f"✓ Hash log transaction successful!")
                return tx_hash_str

            except Exception as e:
                print(f"Hash log transaction failed: {e}")
                return ''
        else:
            print("Hash log transaction skipped (Missing required environment variables)")
            return ''

def generate_report(in_enriched: Path, in_agents: Path, in_final: Path):
    # Get the directory of the output CSV
    output_dir = in_final.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"final_report_{timestamp}.zip"
    zip_path = output_dir / zip_filename
    
    # List of files to look for and include in zip
    files_to_include = [
        in_final,  # The final results we just created
        in_enriched,  # LLM enriched file
        in_agents,   # Agent results file
        output_dir / "prescan_results.csv",
        output_dir / "llm_routed.csv", 
        output_dir / "agent_queues.json"
    ]
    directories_to_include = [
        output_dir / "by_domain"
    ]

    try:
        # Create zip archive with existing files
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            
            for file_path in files_to_include:
                file_obj = Path(file_path)
                
                # Check if file exists (either absolute path or relative to output dir)
                if file_obj.exists():
                    zipf.write(file_obj, arcname=file_obj.name)
                    file_obj.unlink()

            for dir_path in directories_to_include:
                dir_obj = Path(dir_path)
                if dir_obj.exists():
                    for subfile in dir_obj.rglob("*"):
                        zipf.write(subfile, arcname=subfile.relative_to(dir_obj.parent))
                        subfile.unlink()
                    dir_obj.rmdir()

    except Exception as e:
        print(f"Failed to create report: {e}")
        return None
    
    print(f"✓ Created report: {zip_path}")

    # Create hash file for the zip
    hash_filename = f"{zip_filename}.hash"
    hash_path = output_dir / hash_filename
    hash_value = hash(zip_path)
    try:
        with open(hash_path, 'w') as hash_file:
            hash_file.write(f"Hash: {hash_value}\n")
            print(f"✓ Created hash file: {hash_path}")

    except Exception as e:
        print(f"Failed to create hash file: {e}")
        return None
    
    try:
        tx_id = log_on_chain(hash_value)
        if tx_id != '':
            with open(hash_path, 'a') as f:
                f.write(f"View on Etherscan: https://sepolia.etherscan.io/tx/{tx_id}\n")
    except Exception as e:
        print(f"Failed to log transaction on-chain: {e}")
        return None

# ----------------- main -----------------
def finalize(in_enriched: str, in_agents: str, out_csv: str):
    enr = pd.read_csv(in_enriched)
    ag = pd.read_csv(in_agents)

    # Ensure required columns exist
    for col in ["route_agents", "final_domains", "final_primary_regions", "final_related_regulations",
                "input_feature_name", "input_feature_description",
                "expanded_feature_name", "expanded_feature_description"]:
        if col not in enr.columns:
            enr[col] = None

    # Group agent decisions by row_index (index in enriched CSV)
    if "row_index" not in ag.columns:
        raise ValueError("agent_results.csv must contain 'row_index' produced by agent_runner.")

    grouped: Dict[int, pd.DataFrame] = {int(k): v for k, v in ag.groupby("row_index")}

    records: List[Dict[str, Any]] = []
    for idx, row in enr.iterrows():
        feature = row.get("expanded_feature_name") or row.get("input_feature_name") or ""
        desc    = row.get("expanded_feature_description") or row.get("input_feature_description") or ""

        domains = _to_list(row.get("final_domains"))
        regions = _to_list(row.get("final_primary_regions"))
        regs    = _to_list(row.get("final_related_regulations"))

        agents_df = grouped.get(int(idx), pd.DataFrame(columns=["agent","status","score","reasoning"]))

        # --- NEW: prescan fallback when no agents ran ---
        prescan_required = bool(row.get("prescan_required_hint")) \
                           or len(_to_list(row.get("prescan_law_hits"))) > 0
        prescan_boost = float(row.get("prescan_confidence_boost") or 0.0)
        prescan_rationale = (row.get("prescan_rationale") or "").strip()

        if agents_df.empty and prescan_required:
            final_class = "REQUIRED"
            # base 0.70 + your prescan boost (capped 0.95)
            confidence  = min(0.95, round(0.70 + prescan_boost, 2))
            reasoning   = f"Prescan hard hits. {prescan_rationale or 'Law/domain cues detected.'}"
        else:
            # existing path
            final_class = pick_final_class(agents_df)
            confidence  = round(compute_confidence(agents_df, final_class), 2)
            reasoning   = collapse_reasoning(agents_df)

        records.append({
            "feature": feature,
            "description": desc,
            "domain": ", ".join(domains) if domains else "",
            "primary region": ", ".join(regions) if regions else "",
            "regulation hits": ", ".join(regs) if regs else "",
            "clear reasoning": reasoning,
            "confidence": confidence,
            "Final Classification": final_class,
        })

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(out_path, index=False)
    print(f"✓ Wrote final results: {out_path}")
    generate_report(in_enriched, in_agents, out_path)
    print("✓ Done.")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Produce final, audit-ready results table.")
    p.add_argument("--in-enriched", default=IN_ENRICHED_DEFAULT,
                   help="Path to llm_enriched.csv (categorization results)")
    p.add_argument("--in-agents", default=IN_AGENT_DEFAULT,
                   help="Path to agent_results.csv (per-domain agent outcomes)")
    p.add_argument("--out", default=OUT_FINAL_DEFAULT,
                   help="Path to write final results CSV")
    args = p.parse_args()
    finalize(args.in_enriched, args.in_agents, args.out)
