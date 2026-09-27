export type HealthResponse = {
  status: "ok";
  service: "arizonix-api";
  version: string;
};

export type HealthCheckState =
  | { kind: "loading" }
  | { kind: "healthy"; data: HealthResponse }
  | { kind: "error"; message: string };
