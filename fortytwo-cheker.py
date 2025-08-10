import os
import sys
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal, getcontext, ROUND_HALF_UP

import requests
from dotenv import load_dotenv

getcontext().prec = 80

ORANGE = "\033[38;5;208m"
RESET = "\033[0m"
LOGO_ASCII = f"""{ORANGE}
    ______           __       ______             
   / ____/___  _____/ /___  _/_  __/      ______ 
  / /_  / __ \\/ ___/ __/ / / // / | | /| / / __ \\
 / __/ / /_/ / /  / /_/ /_/ // /  | |/ |/ / /_/ /
/_/    \\____/_/   \\__/\\__, //_/   |__/|__/\\____/ 
                     /____/                      
{RESET}"""

EMOJIS = {
    "header": "🎯",
    "wallet": "👛",
    "participant": "👤",
    "rank": "🏆",
    "reward": "💰",
    "activity": "⏱",
    "wins": "✅",
    "winrate": "📊",
    "balance": "🛢️",
    "warn": "⚠️",
    "ok": "✅",
}

@dataclass
class Config:
    api_url: str
    period: str
    page: int
    size: int

    wallets_file: str
    log_mode: str

    bot_token: Optional[str]
    chat_id: Optional[str]

    retry_count: int
    poll_interval_sec: int
    run_once: bool

    mon_rpc_url: str
    mon_decimals: int
    mon_symbol: str
    mon_display_decimals: int


def load_config() -> Config:

    load_dotenv()  # .env in current directory

    return Config(
        api_url=os.getenv("API_URL", "https://jc1n4ugo1k.execute-api.us-east-2.amazonaws.com/leaderboard_v2"),
        period=os.getenv("PERIOD", "all_time"),
        page=int(os.getenv("PAGE", "1")),
        size=int(os.getenv("SIZE", "1")),

        wallets_file=os.getenv("WALLETS_FILE", "wallets.txt"),
        log_mode=os.getenv("LOG_MODE", "CONSOLE_ONLY").upper(),
        bot_token=os.getenv("BOT_TOKEN"),
        chat_id=os.getenv("CHAT_ID"),

        retry_count=int(os.getenv("RETRY_COUNT", "3")),
        poll_interval_sec=int(os.getenv("POLL_INTERVAL_SEC", "1800")),
        run_once=os.getenv("RUN_ONCE", "false").strip().lower() in ("1", "true", "yes"),

        mon_rpc_url=os.getenv("MON_RPC_URL", "https://testnet-rpc.monad.xyz"),
        mon_decimals=int(os.getenv("MON_DECIMALS", "18")),
        mon_symbol=os.getenv("MON_SYMBOL", "MON"),
        mon_display_decimals=int(os.getenv("MON_DISPLAY_DECIMALS", "2")),
    )

def http_get_json(url: str, params: Dict[str, Any], retry_count: int) -> Optional[Dict[str, Any]]:
    last_err = None
    for attempt in range(1, retry_count + 1):
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"[WARN] HTTP {resp.status_code} for {resp.url}", file=sys.stderr)
                last_err = RuntimeError(f"HTTP {resp.status_code}")
        except Exception as e:
            last_err = e
            print(f"[WARN] Request failed (attempt {attempt}/{retry_count}): {e}", file=sys.stderr)
        time.sleep(attempt)  # linear backoff
    print(f"[ERROR] All retries failed: {last_err}", file=sys.stderr)
    return None


def rpc_eth_get_balance(rpc_url: str, address: str, retry_count: int) -> Optional[str]:

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBalance",
        "params": [address, "latest"],
    }
    last_err = None
    for attempt in range(1, retry_count + 1):
        try:
            resp = requests.post(rpc_url, json=payload, timeout=20)
            if resp.status_code != 200:
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                print(f"[WARN] RPC HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
            else:
                j = resp.json()
                if "error" in j:
                    last_err = RuntimeError(str(j["error"]))
                    print(f"[WARN] RPC error: {j['error']}", file=sys.stderr)
                else:
                    return j.get("result")
        except Exception as e:
            last_err = e
            print(f"[WARN] RPC request failed (attempt {attempt}/{retry_count}): {e}", file=sys.stderr)
        time.sleep(attempt)
    print(f"[ERROR] RPC all retries failed: {last_err}", file=sys.stderr)
    return None

def format_activity_time(seconds: float) -> str:
    """Round to whole minutes, then show 'H h M min'."""
    total_minutes = int(round(seconds / 60.0))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours} h {minutes} min"


def compute_win_rate(wins: int, events_participated: int) -> float:
    """wins / events_participated * 100. Safe for zero."""
    if events_participated <= 0:
        return 0.0
    return (wins / events_participated) * 100.0


def wei_hex_to_mon_str(wei_hex: str, base_decimals: int, display_decimals: int = 2) -> Optional[str]:

    try:
        if not wei_hex or not wei_hex.startswith("0x"):
            return None
        wei_int = int(wei_hex, 16)
        q = Decimal(10) ** base_decimals
        mon = Decimal(wei_int) / q
        quant = Decimal(1) / (Decimal(10) ** display_decimals)
        mon_rounded = mon.quantize(quant, rounding=ROUND_HALF_UP)
        fmt = f"{{0:.{display_decimals}f}}"
        return fmt.format(mon_rounded)
    except Exception as e:
        print(f"[WARN] wei_hex_to_mon_str failed: {e}", file=sys.stderr)
        return None


def read_wallets(path: str) -> List[str]:
    wallets = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            wallets.append(s)
    return wallets


def fetch_wallet_record(cfg: Config, wallet: str) -> Optional[Dict[str, Any]]:
    params = {
        "period": cfg.period,
        "page": cfg.page,
        "size": cfg.size,
        "wallet_filter": wallet,
    }
    data = http_get_json(cfg.api_url, params, cfg.retry_count)
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        return None
    return results[0]


def build_summary_message(records: List[Dict[str, Any]], cfg: Config) -> str:
    if not records:
        return f"{EMOJIS['header']} No results found"

    lines = []
    lines.append(f"{EMOJIS['header']} Leaderboard Update")
    lines.append("")

    for r in records:
        participant = str(r.get("participant", ""))
        original = str(r.get("original", ""))  # wallet address from API
        rank = str(r.get("rank", ""))
        total_reward = str(r.get("total_reward", ""))
        wins = int(r.get("wins", 0) or 0)
        events_participated = int(r.get("events_participated", 0) or 0)
        activity_time_sec = float(r.get("activity_time", 0.0) or 0.0)
        mon_balance = r.get("mon_balance", "N/A")

        win_rate = compute_win_rate(wins, events_participated)
        win_rate_str = f"{win_rate:.2f}"
        activity_str = format_activity_time(activity_time_sec)

        lines.append(f"{EMOJIS['participant']} {participant}")
        lines.append(f"{EMOJIS['wallet']} Wallet: {original}")
        lines.append(f"{EMOJIS['rank']} Rank: {rank}")
        lines.append(f"{EMOJIS['reward']} Total reward: {total_reward}")
        lines.append(f"{EMOJIS['activity']} Activity time: {activity_str}")
        lines.append(f"{EMOJIS['wins']} Wins: {wins}")
        lines.append(f"{EMOJIS['winrate']} Win rate: {win_rate_str}%")
        lines.append(f"{EMOJIS['balance']} {cfg.mon_symbol} balance: {mon_balance}")
        lines.append("")

    return "\n".join(lines).strip()


def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            return True
        else:
            print(f"[WARN] Telegram HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[WARN] Telegram send failed: {e}", file=sys.stderr)
        return False


def run_once(cfg: Config) -> None:
    print(LOGO_ASCII)

    print("[INFO] Loading wallets...")
    wallets = read_wallets(cfg.wallets_file)
    print(f"[INFO] Loaded {len(wallets)} wallet(s).")

    records: List[Dict[str, Any]] = []
    for w in wallets:
        print(f"[INFO] Fetching leaderboard data for wallet: {w}")
        rec = fetch_wallet_record(cfg, w)
        if rec is None:
            print(f"[INFO] No result for wallet: {w} (skipped)")
            continue

        print(f"[INFO] Fetching MON balance via RPC for wallet: {w}")
        wei_hex = rpc_eth_get_balance(cfg.mon_rpc_url, w, cfg.retry_count)
        mon_balance_str = "N/A"
        if wei_hex:
            s = wei_hex_to_mon_str(wei_hex, cfg.mon_decimals, cfg.mon_display_decimals)
            if s is not None:
                mon_balance_str = s
            else:
                print(f"[WARN] Failed to convert wei to {cfg.mon_symbol} for {w}", file=sys.stderr)
        else:
            print(f"[WARN] RPC returned no result for {w}", file=sys.stderr)

        rec["mon_balance"] = mon_balance_str
        records.append(rec)

    msg = build_summary_message(records, cfg)

    print("\n[INFO] Summary message:\n" + msg + "\n")

    if cfg.log_mode == "CONSOLE_AND_TELEGRAM":
        if not cfg.bot_token or not cfg.chat_id:
            print("[WARN] BOT_TOKEN or CHAT_ID is missing; Telegram send skipped.", file=sys.stderr)
        else:
            ok = send_telegram(cfg.bot_token, cfg.chat_id, msg)
            if ok:
                print("[INFO] Telegram message sent.")
            else:
                print("[WARN] Telegram message failed.", file=sys.stderr)


def main():
    cfg = load_config()

    if cfg.log_mode not in ("CONSOLE_ONLY", "CONSOLE_AND_TELEGRAM"):
        print("[ERROR] Invalid LOG_MODE. Use CONSOLE_ONLY or CONSOLE_AND_TELEGRAM.", file=sys.stderr)
        sys.exit(1)

    if cfg.size != 1:
        print("[WARN] SIZE is not 1; API may return more than one result.", file=sys.stderr)

    if cfg.run_once:
        run_once(cfg)
        return

    print(f"[INFO] Starting loop. Interval: {cfg.poll_interval_sec}s. Log mode: {cfg.log_mode}.")
    while True:
        run_once(cfg)
        try:
            time.sleep(cfg.poll_interval_sec)
        except KeyboardInterrupt:
            print("\n[INFO] Stopped by user.")
            break


if __name__ == "__main__":
    main()
