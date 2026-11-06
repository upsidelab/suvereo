import type { NextConfig } from "next";
import nextra from "nextra";

const BASE_PATH = "/suvereo";

const nextConfig: NextConfig = {
  output: "export",
  basePath: BASE_PATH,
  env: {
    NEXT_PUBLIC_BASE_PATH: BASE_PATH,
    GTAG_ID: process.env.GTAG_ID,
  },
  images: {
    unoptimized: true,
  },
  trailingSlash: false,
};

const withNextra = nextra({});

export default withNextra(nextConfig);
