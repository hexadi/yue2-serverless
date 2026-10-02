# yue2-serverless

Runpod Serverless worker for [YuE2](https://github.com/multimodal-art-projection/YuE).

This repository keeps the Runpod wrapper separate from the upstream YuE2 runtime and model weights. The default image installs the official `yue2-v0.1.6` release and loads `m-a-p/YuE2-3B` + `m-a-p/YuE2-Vae` at worker startup.

## Baseline

- Linux / Python 3.12
- NVIDIA GPU with BF16 support
- 24 GB VRAM minimum starting point
- One generation request per GPU worker
- 48 kHz stereo output
- Runpod Network Volume is optional but recommended for model caching
- S3-compatible object storage is optional but recommended for generated artifacts

## Request

```json
{
  "input": {
    "style": "Thai indie pop, warm male vocal, electric guitar, synth, 100 BPM",
    "lyrics": "[Verse]\nคืนนี้ยังมีแสงไฟ...",
    "cot": "full",
    "seed": 42
  }
}
```

Supported generation fields are `style`, `lyrics`, `cot`, `seed`, `abc`, `cfg_scale`, `id`, `abc_sampling`, and `semantic_sampling`.

`cot` can be `full`, `melody`, or `off`. Supplying `abc` requires `full` or `melody`. For short smoke tests, you can cap semantic generation with e.g. `"semantic_sampling": {"min_tokens": 64, "max_tokens": 256}`.

## Response

With S3-compatible storage configured:

```json
{
  "job_id": "...",
  "status": "complete",
  "truncated": {},
  "audio_seconds": 123.4,
  "artifacts": {
    "audio.flac": {
      "key": "yue2/jobs/.../audio.flac",
      "url": "https://..."
    }
  }
}
```

Without S3 configuration, artifacts remain in `YUE2_OUTPUT_DIR`. For persistent local artifacts on Runpod Serverless, point that directory into `/runpod-volume`.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `YUE2_MODEL` | `m-a-p/YuE2-3B` | YuE2 model repo or local directory |
| `YUE2_VAE` | `m-a-p/YuE2-Vae` | Listening decoder |
| `YUE2_MODEL_REVISION` | empty | Optional model revision |
| `YUE2_VAE_REVISION` | empty | Optional VAE revision |
| `YUE2_DEVICE` | `cuda` | Inference device |
| `YUE2_MEMORY_BUDGET_GIB` | `24` | YuE2 CUDA memory budget |
| `YUE2_BACKEND` | `torch` | `torch`, `torch-eager`, or `vllm` |
| `YUE2_QUANTIZATION` | `none` | `none` or `fp8` |
| `YUE2_OFFLOAD_AR` | `false` | Offload AR model before acoustic synthesis |
| `YUE2_LOCAL_FILES_ONLY` | `false` | Disable Hub downloads |
| `HF_HOME` | `/root/.cache/huggingface` | Hugging Face cache |
| `HF_TOKEN` | empty | Optional Hugging Face token |
| `RUNPOD_VOLUME_CACHE` | `true` | Use Runpod VolumeCache for HF cache |
| `YUE2_OUTPUT_DIR` | `/tmp/yue2-output` | Temporary/persistent artifact root |
| `YUE2_CLEANUP_AFTER_UPLOAD` | `true` | Remove local job directory after successful S3 upload |
| `S3_BUCKET` | empty | Enables S3-compatible artifact publishing |
| `S3_ENDPOINT_URL` | empty | R2/MinIO/B2/custom S3 endpoint |
| `S3_REGION` | `auto` | S3 region |
| `S3_ACCESS_KEY_ID` | empty | S3 access key |
| `S3_SECRET_ACCESS_KEY` | empty | S3 secret |
| `S3_PUBLIC_BASE_URL` | empty | Optional public base URL; otherwise presigned URLs are returned |
| `S3_PREFIX` | `yue2/jobs` | Object key prefix |
| `S3_URL_TTL_SECONDS` | `86400` | Presigned URL lifetime |
| `YUE2_UPLOAD_ALL_ARTIFACTS` | `false` | Upload all native YuE2 artifacts, including large latent/token files |

## Docker

```bash
docker build -t yue2-serverless .
```

The Dockerfile installs PyTorch 2.10.0 CUDA 12.8 wheels, the official YuE2 release, and the Runpod SDK.

## Runpod Serverless

1. Build/publish the image, or use Runpod's GitHub deployment flow.
2. Create a queue-based Serverless endpoint.
3. Select a BF16-capable GPU with at least 24 GB VRAM.
4. Keep concurrency at one request per worker for the baseline.
5. Attach a Network Volume to reduce repeated Hugging Face downloads.
6. Configure S3-compatible storage if callers need direct artifact URLs.
7. Send generation requests to the endpoint's asynchronous `/run` operation for long songs.

The worker uses the normal Hugging Face cache. For Serverless workers with a Network Volume attached, set `HF_HOME=/runpod-volume/huggingface` so model downloads survive worker replacement. Without a Network Volume, leave the default local cache.

## Local handler test

This does not run YuE2 without a CUDA GPU, but you can validate request handling by importing the validation helpers:

```bash
python -m pytest -q
```

## Upstream and licensing

YuE2 runtime code and model weights are external dependencies and have their own upstream license terms. This repository does not vendor model weights. Review the current upstream code/model licenses before commercial deployment.
