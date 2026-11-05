import {Cards} from "nextra/components"
import { useMDXComponents as getMDXComponents } from "../../mdx-components";
import IntegrationCard from "@/components/integration-card";
import { Metadata } from "next";

const mdxComponents = getMDXComponents({});
const Wrapper = mdxComponents.wrapper;
const P = mdxComponents.p;
const H1 = mdxComponents.h1;
const H2 = mdxComponents.h2;

export const metadata: Metadata = {
  title: "Integrations | Suvereo",
}

export default async function Page() {
  const metadata = {
    title: "Integrations | Suvereo",
    description: "",
  }
  return (
    <Wrapper toc={[]} metadata={metadata} sourceCode={""} >
      <H1>Integrations</H1>
      <P>Suvereo comes with a set of ready-to-use integrations that connect your agents to language models (e.g. Gemini and Azure OpenAI).</P>
      <P>They allow you to leverage enterprise-grade AI models for enhanced security and performance. Furthermore, each of these integrations can be customized and extended by a developer.</P>
      <H2>Language Models</H2>
      <Cards>
        <IntegrationCard name="OpenAI" imageSrc="/tools/suvereo/img/integrations/openai.png" href="/integrations/openai/" />
        <IntegrationCard name="Ollama" imageSrc="/tools/suvereo/img/integrations/ollama.png" href="/integrations/ollama/" />
        <IntegrationCard name="Azure OpenAI" imageSrc="/tools/suvereo/img/integrations/azure-openai.png" href="/integrations/azure-openai/" />
        <IntegrationCard name="Anthropic" imageSrc="/tools/suvereo/img/integrations/anthropic.png" href="/integrations/anthropic/" />
        <IntegrationCard name="Google Gemini" imageSrc="/tools/suvereo/img/integrations/gemini.png" href="/integrations/gemini/" />
        <IntegrationCard name="Mistral" imageSrc="/tools/suvereo/img/integrations/mistral.png" href="/integrations/mistral/" />
      </Cards>
      <H2>Build a Custom Integration</H2>
      <P>These ready-made integrations cover common use cases. If you need to connect a system that isn’t listed here, Suvereo allows you to build custom integrations tailored to your stack.</P>
      <Cards.Card className="x:my-4" title="Learn How to Build a Custom Integration" href="/docs/customization/custom-integration" arrow />
    </Wrapper>
  )
}
