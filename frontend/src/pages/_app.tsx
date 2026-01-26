import "@/styles/globals.css";
import "@mantine/core/styles.css";
import "maplibre-gl/dist/maplibre-gl.css";
import type { AppProps } from "next/app";
import type { NextPage } from "next";
import type { ReactElement, ReactNode } from "react";
import { MantineProvider, createTheme } from "@mantine/core";
import { Layout } from "@/components/Layout";

const theme = createTheme({
  primaryColor: "blue",
});

// Support pages with custom layouts
export type NextPageWithLayout<P = {}, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

export default function App({ Component, pageProps }: AppPropsWithLayout) {
  // If page has custom layout, use it; otherwise use default Layout
  if (Component.getLayout) {
    return (
      <MantineProvider theme={theme} defaultColorScheme="light">
        {Component.getLayout(<Component {...pageProps} />)}
      </MantineProvider>
    );
  }

  return (
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </MantineProvider>
  );
}
