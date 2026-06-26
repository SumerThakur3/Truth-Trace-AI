import { getConfidenceLevel, getConfidenceLabel } from "../src/lib/utils";

describe("Confidence utilities", () => {
  test("getConfidenceLevel returns high for scores >= 90", () => {
    expect(getConfidenceLevel(95)).toBe("high");
    expect(getConfidenceLevel(90)).toBe("high");
  });

  test("getConfidenceLevel returns medium for scores 70-89", () => {
    expect(getConfidenceLevel(85)).toBe("medium");
    expect(getConfidenceLevel(70)).toBe("medium");
  });

  test("getConfidenceLevel returns low for scores below 70", () => {
    expect(getConfidenceLevel(65)).toBe("low");
  });

  test("getConfidenceLabel returns correct labels", () => {
    expect(getConfidenceLabel(95)).toBe("High Confidence");
    expect(getConfidenceLabel(80)).toBe("Medium Confidence");
    expect(getConfidenceLabel(50)).toBe("Low Confidence");
  });
});
