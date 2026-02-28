from sentinelcore.modules.dm_doctor.providers.dm_jobs_trace import DmJobsTraceProvider

def main():
    provider = DmJobsTraceProvider(
        dm_jobs_trace_path="/opt/lsf10/10.1/linux3.10-glibc2.17-x86_64/bin/dm_jobs_trace"
    )

    print("=== CHECK MODE ===")
    result = provider.collect(
        job_id="7859311",     # replace with a real job id
        context_seed={},
        mode="check",
    )

    print("\nArtifacts:")
    print(result.artifacts)

    print("\nWarnings:")
    for w in result.warnings:
        print(" -", w)

    print("\nErrors:")
    for e in result.errors:
        print(" -", e)

    print("\n=== REPLAY MODE ===")
    replay = provider.collect(
        job_id="7859311",
        context_seed={},
        mode="replay",
    )

    print("\nReplay artifacts:", replay.artifacts)
    print("Replay warnings:", replay.warnings)

if __name__ == "__main__":
    main()

