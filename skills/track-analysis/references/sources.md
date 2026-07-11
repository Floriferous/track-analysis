# Sources and upgrade paths

The research (July 2026) this skill's design rests on, and where to go when v0 hits its limits.

## Why this architecture

Claude has no audio input modality — the pipeline converts audio into representations Claude reasons over natively: images and structured data.

- [Vision Language Models Are Few-Shot Audio Spectrogram Classifiers](https://arxiv.org/abs/2411.12058) — validates the spectrogram-as-image approach: VLMs recognize audio content from spectrogram images (GPT-4o hit 59% on ESC-10 zero-tuning). The reason the "look at every image" step works.
- [Exploring Music Transcription with Multi-Modal Language Models](https://medium.com/data-science/exploring-music-transcription-with-multi-modal-language-models-af352105db56) — practical account of what LLMs can/can't extract from music representations.
- [MusTBench: Benchmarking Temporal Grounding in Music LLMs](https://arxiv.org/html/2605.29300) — why audio-native LLMs are *not* yet a substitute: temporal grounding ("what happens at 3:00") is their documented weak spot, especially on dense electronic material. Justifies MIR-tooling as source of truth with any audio-LLM output cross-checked against it.

## Tools used

- [librosa](https://librosa.org/doc/latest/index.html) — onset detection, mel spectrograms, chroma, pYIN pitch tracking, fallback beat tracking. The backbone of both passes.
- libsndfile ≥ 1.1 (via [python-soundfile](https://python-soundfile.readthedocs.io/)) — MP3 decoding without ffmpeg.
- [Beat This!](https://github.com/CPJKU/beat_this) ([paper](https://arxiv.org/pdf/2407.21658)) — primary beat/downbeat grid; runs in seconds on CPU. On well-behaved 4/4 techno it agreed with the kick-anchor heuristic to within ~4 ms in trials — its value is the tracks where the heuristic breaks, plus model-predicted downbeats.
- [Demucs / Hybrid Transformer Demucs](https://github.com/facebookresearch/demucs) ([torchaudio tutorial](https://docs.pytorch.org/audio/stable/tutorials/hybrid_demucs_tutorial.html)) — drums/bass/other/vocals separation in the deep pass; a 90s slice separates in about a minute on CPU.
- [Essentia](https://essentia.upf.edu/) — key/scale extraction (validated against transcribed bass roots where a chroma template failed).
- [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) — EBU R128 integrated/short-term loudness.
- [pretty_midi](https://github.com/craffel/pretty-midi) — the MIDI export tool.

## Upgrade paths

Ordered by expected value for groove/sound-design study:

1. **Waveform-level transient alignment.** Sample-accurate onset marking on separated stems — settles "kick placed late vs slow-bloom kick transient" (failure mode 3) and gives true sub-ms cross-element microtiming. No off-the-shelf tool; small amount of DSP on top of the cached stems.
2. **Synth/chord transcription — [Basic Pitch](https://github.com/spotify/basic-pitch)** (Spotify). Polyphonic transcription of the "other" stem; pYIN in the deep pass is monophonic-bass-only, so chords and stab voicings are currently onset-only.
3. **Per-stem reference similarity — CLAP embeddings.** Embed each cached stem and measure cosine distance to a reference library ([perceptually-aligned similarity](https://arxiv.org/abs/2601.19109), [MERIT](https://arxiv.org/pdf/2605.27346)). Trialed and discriminative — same-element cross-track ~0.75–0.93 vs ~0.4–0.55 across elements — but only pays off at library scale. Gotcha from the trial: use `laion/clap-htsat-unfused`; `laion/larger_clap_music` produced collapsed (all-similar) embeddings under transformers 5.
4. **Drum transcription — [ADT overview](https://www.emergentmind.com/topics/automatic-drum-transcription-adt)**, e.g. ADTOF-class models. Kick/snare/hat/tom/cymbal *classification* instead of the frequency-band proxy; recent work combines it with drum-stem separation ([Enhanced ADT via drum stem separation](https://arxiv.org/html/2509.24853v1)).
5. **Arrangement-resolved deep metrics.** Pump depth, stereo width, and kick anatomy computed per section instead of per slice — producers automate these between sections; pure extension of existing code.
6. **Audio-native captioning — [Music Flamingo](https://research.nvidia.com/labs/adlr/MF/)** ([weights](https://huggingface.co/nvidia/music-flamingo-hf)) for GPU environments, or [Gemini audio understanding](https://ai.google.dev/gemini-api/docs/audio) as a hosted option. Timestamped perceptual vocabulary (texture, timbre words) the MIR path lacks; cross-check against the dossier, per MusTBench above.
7. **Timestamped captioning research** — [TAC: Timestamped Audio Captioning](https://arxiv.org/html/2602.15766v1), [SonicVerse](https://arxiv.org/pdf/2506.15154) — the research frontier for "sounds at time t" as a single model call; not yet production-ready for this use, worth re-checking periodically.
