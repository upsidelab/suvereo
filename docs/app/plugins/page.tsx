import {Cards} from "nextra/components"
import { useMDXComponents as getMDXComponents } from "../../mdx-components";
import IntegrationCard from "@/components/integration-card";
import { Metadata } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH;
const mdxComponents = getMDXComponents({});
const Wrapper = mdxComponents.wrapper;
const P = mdxComponents.p;
const A = mdxComponents.a;
const H1 = mdxComponents.h1;
const H2 = mdxComponents.h2;

export const metadata: Metadata = {
  title: "Plugins | Suvereo",
}

export default async function Page() {
  const metadata = {
    title: "Plugins | Suvereo",
    description: "",
  }
  return (
    <Wrapper toc={[]} metadata={metadata} sourceCode={""} >
      <H1>Plugins</H1>
      <P>Suvereo comes with a set of ready-to-use plugins that connect your agents to the language models and tools they need (e.g. Gemini and Azure OpenAI).</P>
      <P>They allow you to leverage enterprise-grade AI models for enhanced security and performance. Furthermore, each of these plugins can be customized and extended by a developer.</P>
      <H2>Language Models</H2>
      <Cards>
        <IntegrationCard name="OpenAI" imageSrc={`${basePath}/img/integrations/openai.png`} href="/plugins/openai/" />
        <IntegrationCard name="Ollama" imageSrc={`${basePath}/img/integrations/ollama.png`} href="/plugins/ollama/" />
        <IntegrationCard name="Azure OpenAI" imageSrc={`${basePath}/img/integrations/azure-openai.png`} href="/plugins/azure-openai/" />
        <IntegrationCard name="Anthropic" imageSrc={`${basePath}/img/integrations/anthropic.png`} href="/plugins/anthropic/" />
        <IntegrationCard name="Google Gemini" imageSrc={`${basePath}/img/integrations/gemini.png`} href="/plugins/gemini/" />
        <IntegrationCard name="Mistral" imageSrc={`${basePath}/img/integrations/mistral.png`} href="/plugins/mistral/" />
      </Cards>
      <H2>Integrations</H2>
      <P>Suvereo provides an <A href="/plugins/mcp">MCP integration</A> that connects to MCP servers, so your agents can use the tools those servers offer.</P>
      <P>It also lets you onboard integrations of your own. They can feed agents with data, let them act in external systems and provide them with tools. <A href="/docs/customization/integrations">Learn how integrations work</A>.</P>
      <H2>Enthusiast: Ecommerce Domain Definition</H2>
      <P>Enthusiast brings Suvereo to online stores. It comes with ready-made integrations for connecting to e-commerce systems, and ready-made agents that, for example, search the catalog, take in orders and enrich product data. <A href="/tools/enthusiast">Explore Enthusiast</A>.</P>
    </Wrapper>
  )
}
