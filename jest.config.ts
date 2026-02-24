import type { Config } from "jest";

const config: Config = {
  testEnvironment: "node",
  roots: ["<rootDir>/tests/unit"],
  transform: {},
  moduleFileExtensions: ["ts", "tsx", "js"],
  testRegex: "(/tests/unit/.*|(\\.|/)(test|spec))\\.ts$"
};

export default config;
