/// <reference types="vite/client" />

/**
 * API Configuration for Localhost, Render, and Vercel environments.
 */

const metaEnv = (import.meta as unknown as { env?: Record<string, string> }).env
const rawUrl = metaEnv?.VITE_API_BASE_URL?.trim()

// In local dev and Vercel proxy, relative path '' ensures zero CORS/IP mismatch errors
export const API_BASE_URL: string = rawUrl ? rawUrl.replace(/\/+$/, '') : ''
