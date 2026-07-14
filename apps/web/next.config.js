//@ts-check

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Root package.json / workspace files were removed, so Turbopack infers the
  // wrong workspace root by walking up. Pin it to this app directory.
  turbopack: {
    root: __dirname,
  },
  // The Claude Agent SDK spawns the bundled Claude Code CLI as a subprocess.
  // Keep it external so the bundler doesn't rewrite its executable-path
  // resolution and break the spawn.
  serverExternalPackages: ['@anthropic-ai/claude-agent-sdk'],
  experimental: {
    // The @phosphor-icons/react root is a barrel re-exporting thousands of
    // icons — Turbopack compiles the whole barrel on first request. Rewrite
    // imports to direct icon paths so only the used icons compile.
    optimizePackageImports: ['@phosphor-icons/react'],
  },
};

module.exports = nextConfig;
