/// <reference types="vite/client" />

/**
 * API Configuration for Localhost, Render, and Vercel environments.
 */

const metaEnv = (import.meta as unknown as { env?: Record<string, string> }).env
const rawUrl = metaEnv?.VITE_API_BASE_URL?.trim()

export const API_BASE_URL: string = rawUrl
  ? rawUrl.replace(/\/+$/, '')
  : typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://127.0.0.1:8000'
  : ''
