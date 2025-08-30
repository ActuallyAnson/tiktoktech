# src/pipelines/run_all.py
from __future__ import annotations
import argparse, os, sys, subprocess, time, shlex, textwrap
from pathlib import Path
import platform

def q(s: str) -> str:
    """Cross-platform CLI arg quoting.
    - Windows: wrap in double quotes (handles backslashes, spaces)
    - Unix: use shlex.quote
    """
    s = str(s)
    if platform.system() == "Windows":
        # Escape any embedded double quotes
        s = s.replace('"', r'\"')
        return f'"{s}"'
    return shlex.quote(s)

# Optional pretty UI; falls back to prints if not installed
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    RICH = True
    console = Console()
except Exception:
    RICH = False
    console = None

def run(cmd: str, log_path: Path) -> int:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"   # make child Python use UTF-8 for stdio
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write(f"$ {cmd}\n\n")
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
        )
        start = time.time()
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                logf.write(line)
                if not RICH:
                    print(line, end="")
        rc = proc.wait()
    return rc

def main():
    p = argparse.ArgumentParser(
        description="End-to-end compliance pipeline runner (prescan → enrich → route → agents → finalize)."
    )
    p.add_argument("--input", default="data/sample_features.csv")
    p.add_argument("--terms", default="data/terminology.json")
    p.add_argument("--outdir", default="outputs")
    # Routing/agent knobs (match your existing CLIs)
    p.add_argument("--only-llm", action="store_true", help="Router: only rows with non-empty llm_domains")
    p.add_argument("--llm-all", action="store_true", help="Agent runner: send every row to the LLM")
    p.add_argument("--llm-for-llm-categorized", action="store_true",
                   help="Agent runner: LLM only for rows with llm_domains")
    p.add_argument("--workers", type=int, default=8, help="Agent runner: parallel workers")
    p.add_argument("--llm-min-interval", type=float, default=1.0, help="Min seconds between LLM calls")
    p.add_argument("--llm-jitter", type=float, default=0.0, help="Extra random delay per LLM call")
    p.add_argument("--skip-prescan", action="store_true")
    p.add_argument("--skip-enrich", action="store_true")
    p.add_argument("--skip-route", action="store_true")
    p.add_argument("--skip-agents", action="store_true")
    p.add_argument("--skip-final", action="store_true")
    args = p.parse_args()

    out = Path(args.outdir)
    paths = {
        "prescan_csv": out / "prescan_results.csv",
        "by_domain_dir": out / "by_domain",
        "domain_none": out / "by_domain" / "domain__NONE.csv",
        "enriched_csv": out / "llm_enriched.csv",
        "routed_csv": out / "llm_routed.csv",
        "queues_json": out / "agent_queues.json",
        "queues_dir": out / "queues",
        "agent_results": out / "agent_results.csv",
        "final_csv": out / "final_results.csv",
        "logs_dir": out / "logs",
    }

    # Build commands (string form for nice logging)
    cmds = []

    if not args.skip_prescan:
        cmds.append((
            "Prescan",
            f"python -m src.pipelines.prescan_pipeline "
            f"--input {q(args.input)} "
            f"--terms {q(args.terms)} "
            f"--out {q(paths['prescan_csv'])} "
            f"--split {q(paths['by_domain_dir'])}"
        ))

    if not args.skip_enrich:
        cmds.append((
            "LLM Enrichment (NONE)",
            f"python -m src.pipelines.llm_enrichment_none "
            f"--prescan {q(paths['prescan_csv'])} "
            f"--none {q(paths['domain_none'])} "
            f"--out {q(paths['enriched_csv'])}"
        ))

    if not args.skip_route:
        only_llm_flag = " --only-llm" if args.only_llm else ""
        cmds.append((
            "Router",
            f"python -m src.pipelines.router_cli "
            f"--in {q(paths['enriched_csv'])} "
            f"--out {q(paths['routed_csv'])} "
            f"--queues-out {q(paths['queues_json'])} "
            f"--split-dir {q(paths['queues_dir'])}"
            f"{only_llm_flag}"
        ))

    if not args.skip_agents:
        # prefer llm-all if both flags given
        llm_flag = " --llm-all" if args.llm_all else (" --llm-for-llm-categorized" if args.llm_for_llm_categorized else "")
        cmds.append((
            "Agents",
            f"python -m src.pipelines.agent_runner "
            f"--in {q(paths['routed_csv'])} "
            f"--out {q(paths['agent_results'])}"
            f"{llm_flag} "
            # f"--workers {args.workers} "
            # f"--llm-min-interval {args.llm_min_interval} "
            # f"--llm-jitter {args.llm_jitter}"
        ))

    if not args.skip_final:
        cmds.append((
            "Finalize",
            f"python -m src.pipelines.finalize_results "
            f"--in-enriched {q(paths['enriched_csv'])} "
            f"--in-agents {q(paths['agent_results'])} "
            f"--out {q(paths['final_csv'])}"
        ))

    # Run with progress
    start_all = time.time()
    if RICH:
        console.rule("[bold cyan]Compliance Pipeline")
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task("Starting…", total=len(cmds))
            for i, (label, cmd) in enumerate(cmds, 1):
                progress.update(task, description=f"[bold]{label}[/]")

                log_file = paths["logs_dir"] / f"{i:02d}_{label.lower().replace(' ', '_')}.log"
                rc = run(cmd, log_file)
                if rc != 0:
                    progress.stop()
                    if console:
                        console.print(f"[red]✗ {label} failed (exit {rc}). See log: {log_file}")
                    sys.exit(rc)
                progress.advance(task)
        dur = time.time() - start_all
        console.print(f"All done in {dur:.1f}s")
    else:
        print("== Compliance Pipeline ==")
        for i, (label, cmd) in enumerate(cmds, 1):
            print(f"\n[{i}/{len(cmds)}] {label}\n$ {cmd}")
            log_file = paths["logs_dir"] / f"{i:02d}_{label.lower().replace(' ', '_')}.log"
            rc = run(cmd, log_file)
            if rc != 0:
                print(f" {label} failed (exit {rc}). See log: {log_file}")
                sys.exit(rc)
        dur = time.time() - start_all
        print(f"\nAll done in {dur:.1f}s")
        

if __name__ == "__main__":
    main()
