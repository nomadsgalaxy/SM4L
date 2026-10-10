#!/usr/bin/env bash
# Sourced by launch_proton.sh. On a hybrid laptop the display is driven by the integrated GPU, and Wine's OpenGL lands on it unless
# the NVIDIA GPU is asked for. This sets NVIDIA's PRIME render offload variables when it is safe to:
#   SM4L_GPU=auto (default)  only when an NVIDIA GPU and another GPU both exist and no NVIDIA output is connected
#   SM4L_GPU=nvidia          always
#   SM4L_GPU=none            never
# Variables you already set are kept. SM4L_DRM_ROOT replaces /sys/class/drm (for the test). Sets SM4L_GPU_NOTE to one line saying what happened.
sm4l_gpu_env() {
  local mode="${SM4L_GPU:-auto}" root="${SM4L_DRM_ROOT:-/sys/class/drm}" card vendor nvidia=0 other=0 connected=0 out
  case "$mode" in none|nvidia|auto) ;; *) SM4L_GPU_NOTE="gpu: SM4L_GPU=$mode is not none, nvidia or auto; leaving the GPU choice alone"; return 0 ;; esac
  if [[ "$mode" == none ]]; then SM4L_GPU_NOTE="gpu: SM4L_GPU=none, leaving the GPU choice alone"; return 0; fi
  for card in "$root"/card[0-9]*; do
    [[ "$card" == *-* || ! -r "$card/device/vendor" ]] && continue
    vendor="$(<"$card/device/vendor")"
    if [[ "$vendor" == 0x10de ]]; then
      nvidia=1
      for out in "$root/$(basename -- "$card")"-*/status; do [[ -r "$out" && "$(<"$out")" == connected ]] && connected=1; done
    else
      other=1
    fi
  done
  if [[ "$mode" == auto ]]; then
    if (( ! nvidia )); then SM4L_GPU_NOTE="gpu: no NVIDIA GPU found, leaving the GPU choice alone"; return 0; fi
    if (( ! other )); then SM4L_GPU_NOTE="gpu: only an NVIDIA GPU found, leaving the GPU choice alone"; return 0; fi
    if (( connected )); then SM4L_GPU_NOTE="gpu: the NVIDIA GPU drives the display, leaving the GPU choice alone"; return 0; fi
  fi
  [[ -v __NV_PRIME_RENDER_OFFLOAD ]] || export __NV_PRIME_RENDER_OFFLOAD=1
  [[ -v __GLX_VENDOR_LIBRARY_NAME ]] || export __GLX_VENDOR_LIBRARY_NAME=nvidia
  [[ -v __VK_LAYER_NV_optimus ]] || export __VK_LAYER_NV_optimus=NVIDIA_only
  SM4L_GPU_NOTE="gpu: SM4L_GPU=$mode, NVIDIA render offload on (__NV_PRIME_RENDER_OFFLOAD=$__NV_PRIME_RENDER_OFFLOAD __GLX_VENDOR_LIBRARY_NAME=$__GLX_VENDOR_LIBRARY_NAME)"
}
sm4l_gpu_env
