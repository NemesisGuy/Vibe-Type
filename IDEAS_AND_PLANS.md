# VibeType Ideation & Planning

This document is for brainstorming, technical planning, and capturing ideas for the VibeType project. It is especially focused on maximizing performance and features with an NVIDIA 1080 Ti GPU.

---

## Hardware Notes & Constraints

- **GPU:** NVIDIA 1080 Ti (11GB VRAM, CUDA support, no Tensor cores)
- **Strengths:**
  - Good CUDA performance for its generation
  - Can run most ONNX and PyTorch models with proper optimization
  - 11GB VRAM allows decent model sizes
- **Limits:**
  - No FP16/Tensor core acceleration (unlike RTX cards)
  - VRAM may limit very large models or batch sizes
  - CUDA 12.x not supported (max CUDA 11.x)

---

## Recently Implemented ✅

### Thinking Fillers System (September 2025)
- **Feature:** Natural filler phrases during AI processing
- **Implementation:** 40+ contextual phrases spoken while Ollama thinks
- **Configuration:** Customizable timing intervals and enable/disable toggle
- **Benefits:** Eliminates awkward silence, provides user feedback, keeps conversations natural
- **Files:** `core/thinking_fillers.py`, integrated into `core/ai.py` and `core/app_state.py`

### MCP Server Integration
- **Feature:** VibeType now manages MCP server as subprocess
- **Implementation:** Auto-start, manual controls, status indicators, log viewing
- **Benefits:** No more manual terminal management for MCP server

---

## Feature Ideas

### Short-Term (1080 Ti Optimized)
- **Real-time TTS streaming** with low latency chunking
- **Voice blending UI** for custom voice creation (GPU-accelerated mixing)
- **Per-language voice selection** with automatic switching
- **User-editable pronunciation dictionary** for technical terms
- **Visual feedback** for language detection and voice switching
- **GPU benchmarking tool** to compare CPU vs CUDA performance
- **Model quantization** to fit more voices in 11GB VRAM
- **Batch TTS processing** for long documents (utilize full GPU memory)

### Medium-Term
- **Web-based remote control** API for mobile/tablet control
- **Multi-user voice chat** with individual TTS voices
- **Browser extension integration** for reading web pages
- **Custom hotkey profiles** for different applications
- **Voice activity detection** to improve dictation accuracy
- **Automatic model switching** based on content type

### Long-Term & Experimental
- **AI-powered voice style transfer** (within 1080 Ti constraints)
- **Real-time voice conversion** for privacy
- **Distributed processing** across multiple machines
- **Custom model training** pipeline for personalized voices
- **Advanced phoneme editing** for perfect pronunciation

---

## Technical Experiments & Benchmarks

### Performance Testing
- Compare TTS speed and quality: CPU vs 1080 Ti CUDA
- Test model quantization (ONNX 8-bit/16-bit) impact on quality
- Measure VRAM usage patterns for different model sizes
- Profile memory allocation and deallocation efficiency
- Test concurrent model loading (multiple languages)

### Optimization Research
- **ONNX Runtime GPU acceleration** for all TTS models
- **Mixed precision inference** where supported
- **Memory-mapped model loading** to reduce startup time
- **Async model switching** to eliminate loading delays
- **GPU memory pooling** to prevent fragmentation

### Hardware Utilization
- **CUDA stream optimization** for parallel processing
- **Memory bandwidth testing** with different batch sizes
- **Thermal monitoring** during extended usage
- **Power consumption analysis** for different workloads

---

## 1080 Ti Specific Optimizations

### Memory Management
- **Smart model caching:** Keep frequently used voices in VRAM
- **Progressive loading:** Stream large models as needed
- **Compression techniques:** Use quantized models by default
- **Memory defragmentation:** Periodic cleanup of GPU memory

### Performance Tuning  
- **CUDA kernel optimization** for older architecture
- **Batch size tuning** to maximize throughput without OOM
- **Pipeline parallelism** between CPU preprocessing and GPU inference
- **Asynchronous processing** to hide model loading latency

### Quality vs Speed Trade-offs
- **Fast mode:** Lower quality, higher speed for real-time use
- **Quality mode:** Full precision for final output
- **Adaptive quality:** Dynamic adjustment based on content length
- **User preferences:** Let users choose their preferred balance

---

## Integration Ideas

### MCP Expansions
- **YouTube MCP:** Extract and read video transcripts
- **Web scraping MCP:** Read articles and summaries aloud  
- **Weather MCP:** Voice weather reports with personality
- **Calendar MCP:** Spoken schedule and reminders
- **System monitoring MCP:** Voice system status updates
- **File management MCP:** Voice-controlled file operations

### Third-Party Integration
- **OBS Studio plugin:** Voice announcements for streaming
- **Discord bot:** TTS for text channels
- **VSCode extension:** Code reading and documentation
- **Browser extension:** Read-aloud for any webpage
- **Home automation:** Voice feedback for smart home actions

---

## Research Areas

### AI & Machine Learning
- **Lightweight voice cloning** that runs on 1080 Ti
- **Real-time emotion detection** for expressive TTS
- **Content-aware voice selection** (technical vs casual)
- **Pronunciation learning** from user corrections

### Audio Processing
- **Advanced noise reduction** for better dictation
- **Echo cancellation** for hands-free operation
- **Audio enhancement** for clearer synthetic speech
- **Spatial audio effects** for immersive experience

### User Experience
- **Accessibility features** for visually impaired users
- **Gesture control** integration
- **Eye tracking** for hands-free text selection
- **Voice emotion analysis** for better interaction

---

## Development Priorities

### High Priority
1. Optimize existing TTS models for 1080 Ti
2. Implement model quantization pipeline
3. Add voice blending interface
4. Create comprehensive benchmarking suite

### Medium Priority  
1. Web API for remote control
2. Browser extension development
3. Advanced hotkey customization
4. Multi-language optimization

### Low Priority (Future)
1. Custom model training pipeline
2. Advanced AI features
3. Hardware-specific optimizations for newer GPUs
4. Cloud integration options

---

## Notes & Reminders

- Always test new features on 1080 Ti before release
- Maintain compatibility with CPU-only systems
- Document performance characteristics for each feature
- Keep user configuration simple but powerful
- Prioritize local-first, privacy-focused design
