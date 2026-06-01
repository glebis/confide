# CONFIDE — Red/Green isolation, VMs, and encryption at rest

Turning the privacy *convention* (anonymize-before-cloud) into an **enforced boundary**.
Three layers, strongest last. On this machine: **macOS 26 (Tahoe)** + **sops 3.12.2** +
**age** are present, so all three are available today.

## The Red/Green model

- **RED** = raw transcripts (real PII). Never leaves the local trust boundary.
- **Pipeline** = the local CONFIDE stack (regex + Natasha + local LLM). No cloud.
- **GREEN** = redacted, reviewed output. The **only** thing published to where a cloud
  agent can read it.

The agent passes a RED path and only ever reads GREEN. `confide redact <red> --out <green>`
and `confide stats <red>` already guarantee **stdout/JSON carry no PII** — only aggregates.

## Layer 1 — process isolation (today, no extra tooling)

`confide stats` / `redact` read RED locally and emit only GREEN + aggregate manifests.
Convention-enforced; good enough for a trusted single machine.

## Layer 2 — container isolation (Docker, no network)

Run the pipeline in a container with **no egress**, RED mounted **read-only**, GREEN
read-write — see `eval/docker-compose.yml`. Harden with `network_mode: none` for the
redaction stage (the local LLM sibling lives on an `internal: true` network so RED-derived
prompts can't reach the internet):

```yaml
services:
  llm:        { networks: [vault], image: ghcr.io/ggml-org/llama.cpp:server, ... }
  confide:
    networks: [vault]
    volumes:
      - ./RED:/red:ro          # raw in, read-only
      - ./GREEN:/green          # redacted out, the only writable path
    environment: [ "LLM_API=openai", "LLM_BASE_URL=http://llm:8080" ]
networks:
  vault: { internal: true }    # no route to the internet
```

## Layer 3 — VM isolation (macOS-native, strongest)

A VM gives **hardware-level** isolation of RED, not just a namespace. On macOS 26:

- **Apple `container`** (built on Virtualization.framework) runs each Linux container in
  its **own lightweight VM** — stronger than Docker Desktop's shared VM.
  `brew install container` (or Apple's release), then `container run --network none …`.
- **Lima / Colima** — Docker-compatible Linux VMs (`colima start --network-address=false`).
- **Tart / UTM** — full VM managers if you want a sealed appliance.

Pattern: a sealed, network-less VM mounts RED, runs CONFIDE + a local LLM inside, and
publishes only GREEN to a shared folder. RED plaintext never exists outside the VM.

## Encryption at rest — sops + age (installed)

Keep RED as **ciphertext on disk**; decrypt only in-memory inside the isolated VM/container.

```bash
# one-time: a local age key (never leaves the machine)
age-keygen -o ~/.config/confide/age.key
export SOPS_AGE_RECIPIENTS=$(age-keygen -y ~/.config/confide/age.key)

# encrypt a raw transcript at rest (RED stays ciphertext on disk)
sops --encrypt --input-type binary --output-type binary session.md > session.md.sops

# inside the sealed VM/container: decrypt to a tmpfs, redact, publish GREEN, wipe
export SOPS_AGE_KEY_FILE=~/.config/confide/age.key
sops --decrypt --input-type binary --output-type binary session.md.sops \
  | python3 confide.py redact /dev/stdin --out /green
```

sops also guards any **cloud secrets** (API keys) if you later add a frontier-model
CONFIDE-Red attacker — encrypt `secrets.yaml` with sops, decrypt at runtime.

## Recommended posture

- **Synthetic data / dev:** Layer 1 (process) — fast, zero setup.
- **Real personal sessions, local-only:** Layer 2 (no-network container) + sops at rest.
- **Real data, maximum assurance / shareable appliance:** Layer 3 (sealed VM) + sops.

In every posture the rule is identical: **RED in, GREEN out, nothing else crosses.**
