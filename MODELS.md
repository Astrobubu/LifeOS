# OpenAI Models Reference for LifeOS

## Models Currently Used in LifeOS

| Purpose | Model | Location |
|---------|-------|----------|
| **Main LLM** | `gpt-5-mini` | `config/settings.py` → `OPENAI_MODEL` |
| **Vision** | `gpt-5` | `config/settings.py` → `OPENAI_VISION_MODEL` |
| **Transcription** | `gpt-4o-transcribe` | `agent/smart_agent.py` → `process_voice()` |
| **Embeddings** | `text-embedding-3-small` | `memory/vector_memory.py` |
| **Fallback Pricing** | `gpt-5-nano` | `utils/cost_tracker.py` |

---

## All OpenAI API Models (2025)

### GPT-5 Series
| Model | API Name | Best For |
|-------|----------|----------|
| GPT-5 | `gpt-5` | Flagship model, agentic tasks, 256k context, multimodal |
| GPT-5.2 | `gpt-5.2` | Leading model for coding and agentic tasks |
| GPT-5.1 | `gpt-5.1` | Mid-tier GPT-5 variant |
| GPT-5 Mini | `gpt-5-mini` | Fast, cost-efficient, well-defined tasks |
| GPT-5 Nano | `gpt-5-nano` | Fastest, most cost-efficient, minimal resources |

### GPT-4o Series
| Model | API Name | Best For |
|-------|----------|----------|
| GPT-4o | `gpt-4o` | Omni model, text/vision/audio, multilingual |
| GPT-4o Mini | `gpt-4o-mini` | Legacy fast/cheap option |
| GPT-4o Transcribe | `gpt-4o-transcribe` | Audio transcription |
| GPT-4o Mini Transcribe | `gpt-4o-mini-transcribe` | Fast audio transcription |

### GPT-4.1 Series
| Model | API Name | Best For |
|-------|----------|----------|
| GPT-4.1 | `gpt-4.1` | Coding, instruction-following, long context |
| GPT-4.1 Mini | `gpt-4.1-mini` | Faster 4.1 variant |
| GPT-4.1 Nano | `gpt-4.1-nano` | Cheapest 4.1 variant |

### O-Series (Reasoning Models)
| Model | API Name | Best For |
|-------|----------|----------|
| o3 | `o3` | Logic powerhouse, scientific tasks, deep reasoning |
| o3 Mini | `o3-mini` | Fast reasoning, STEM, coding |
| o4 Mini | `o4-mini` | Technical intelligence, affordable |
| o4 Mini High | `o4-mini-high` | Better at coding and visual input |
| o1 | `o1` | Previous reasoning model (deprecated) |

### Specialized Models
| Model | API Name | Best For |
|-------|----------|----------|
| Text Embedding 3 Small | `text-embedding-3-small` | Semantic search, embeddings |
| Text Embedding 3 Large | `text-embedding-3-large` | High-quality embeddings |
| GPT Image 1.5 | `gpt-image-1.5` | Image generation, editing |
| Sora 2 | `sora-2` | Video generation |
| Sora 2 Pro | `sora-2-pro` | Pro video generation |
| GPT Realtime | `gpt-realtime` | Real-time audio I/O |
| GPT Audio | `gpt-audio` | Audio processing |
| Omni Moderation | `omni-moderation-latest` | Content moderation |

---

## Quick Reference for Switching Models

To change a model in LifeOS:

1. **Main LLM**: Edit `OPENAI_MODEL` in `.env` or `config/settings.py`
2. **Vision**: Edit `OPENAI_VISION_MODEL` in `.env` or `config/settings.py`
3. **Transcription**: Edit hardcoded value in `agent/smart_agent.py` line ~594
4. **Embeddings**: Edit in `memory/vector_memory.py`

---

## Pricing Tiers (per 1M tokens)

| Model | Input | Output |
|-------|-------|--------|
| gpt-5-nano | ~$0.10 | ~$0.40 |
| gpt-5-mini | $0.25 | $2.00 |
| gpt-5 | ~$2.50 | ~$10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| text-embedding-3-small | $0.02 | - |

*Note: Prices are approximate and may change. Check OpenAI pricing page for current rates.*
