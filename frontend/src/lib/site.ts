export const siteConfig = {
  name: "Iris",
  // Update the base URL to point at Iris.  The original code referenced
  // the Suna domain; Iris uses its own domain.  Update this if you
  // deploy under a different host.
  url: "https://irisai.vision/",
  description: "Iris AI",
  links: {
    // Update to Iris social accounts.  Note that the GitHub
    // organization remains kortix-ai/iris because the repository is hosted
    // under that organization, but future forks may change this.
    twitter: "https://x.com/irisai",
    github: "https://github.com/kortix-ai/iris",
    linkedin: "https://www.linkedin.com/company/irisai/",
  },
};

export type SiteConfig = typeof siteConfig;
