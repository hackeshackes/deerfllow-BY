/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially useful
 * for Docker builds.
 */
import "./src/env.js";

function getInternalServiceURL(envKey, fallbackURL) {
  const configured = process.env[envKey]?.trim();
  return configured && configured.length > 0
    ? configured.replace(/\/+$/, "")
    : fallbackURL;
}
// import nextra from "nextra";
// const withNextra = nextra({});

/** @type {import("next").NextConfig} */
const config = {
  devIndicators: false,
  async rewrites() {
    const beforeFiles = [];
    const fallback = [];
    const langgraphURL = getInternalServiceURL(
      "DEER_FLOW_INTERNAL_LANGGRAPH_BASE_URL",
      "http://127.0.0.1:2024",
    );
    const gatewayURL = getInternalServiceURL(
      "DEER_FLOW_INTERNAL_GATEWAY_BASE_URL",
      "http://127.0.0.1:8001",
    );

    if (!process.env.NEXT_PUBLIC_LANGGRAPH_BASE_URL) {
      beforeFiles.push({
        source: "/api/langgraph",
        destination: langgraphURL,
      });
      beforeFiles.push({
        source: "/api/langgraph/:path*",
        destination: `${langgraphURL}/:path*`,
      });
    }

    if (!process.env.NEXT_PUBLIC_BACKEND_BASE_URL) {
      fallback.push({
        source: "/api/:path*",
        destination: `${gatewayURL}/api/:path*`,
      });
    }

    return {
      beforeFiles,
      afterFiles: [],
      fallback,
    };
  },
};

// export default withNextra(config);
export default config;
