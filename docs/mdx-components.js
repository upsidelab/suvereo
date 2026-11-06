import { useMDXComponents as getThemeComponents } from "nextra-theme-docs";

const themeComponents = getThemeComponents();
const ThemeAnchor = themeComponents.a;

// Links to sibling sites on the same domain (e.g. /tools/enthusiast) must not get this site's basePath
// prepended, which next/link does for every root-relative href. Render them as plain anchors instead.
function Anchor({ href, className, ...props }) {
  if (typeof href === "string" && href.startsWith("/tools/")) {
    return (
      <a
        href={href}
        className={`x:text-primary-600 x:underline x:hover:no-underline x:decoration-from-font x:[text-underline-position:from-font] ${className ?? ""}`}
        {...props}
      />
    );
  }
  return <ThemeAnchor href={href} className={className} {...props} />;
}

export function useMDXComponents(components) {
  return {
    ...themeComponents,
    a: Anchor,
    ...components
  };
}
