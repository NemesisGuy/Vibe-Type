# VibeType Ideation & Planning

This document is for brainstorming, technical planning, and capturing ideas for the VibeType project. It is especially focused on maximizing performance and features with an NVIDIA 1080 Ti GPU.

---

## Hardware Notes & Constraints

- **GPU:** NVIDIA 1080 Ti (11GB VRAM, CUDA support, no Tensor cores)
- **Strengths:**
  - Good CUDA performance for its generation
  - Can run most ONNX and PyTorch models with proper optimization
- **Limits:**
  - No FP16/Tensor core acceleration (unlike RTX cards)
  - VRAM may limit very large models or batch sizes
  - CUDA 12.x not supported (max CUDA 11.x)

---

## Feature Ideas

### Short-Term
- Real-time TTS streaming with low latency
- Voice blending UI for custom voices
- Per-language voice selection
- User-editable pronunciation dictionary
- Visual feedback for language detection
- Hotkey to benchmark TTS speed (CPU vs GPU)

### Long-Term
- Web-based remote control or API
- Multi-user voice chat with TTS
- Automatic model quantization for low VRAM
- Integration with browser extensions
- AI-powered voice style transfer

---

## Technical Experiments & Benchmarks
- Compare TTS speed and quality: CPU vs 1080 Ti (CUDA)
- Test model quantization (e.g., ONNX 8-bit/16-bit)
- Batch synthesis for long-form text
- Measure VRAM usage for different models
- Try streaming synthesis with chunked audio
- Profile memory and latency bottlenecks

---

## Optimization Opportunities
- Use ONNX Runtime with CUDA for TTS
- Quantize models to fit larger voices in VRAM
- Implement smart batching for multi-sentence input
- Cache frequent voices or phoneme sequences
- Fallback to CPU if GPU is busy or out of memory

---

## Open Questions & Research Links
- What is the largest TTS model that fits in 11GB VRAM?
- Are there open-source tools for easy ONNX quantization?
- Can we use mixed precision on 1080 Ti for speedup?
- How to best handle multi-language streaming on limited VRAM?
- [ONNX Runtime GPU docs](https://onnxruntime.ai/docs/build/eps.html#cuda)
- [NVIDIA 1080 Ti specs](https://www.techpowerup.com/gpu-specs/geforce-gtx-1080-ti.c2996)

---

## Next Steps / Action Items
- [ ] Run a TTS speed benchmark on 1080 Ti vs CPU
- [ ] Try quantizing a Kokoro or Piper model
- [ ] Prototype a real-time streaming TTS endpoint
- [ ] Add your own ideas and notes below!

---

## Your Brainstorming Space

(Add your thoughts, wild ideas, and questions here)

- 

