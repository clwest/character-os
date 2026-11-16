import { expect, type Page } from "@playwright/test";

/** Create and select a Universe through the same inline UI used by operators. */
export async function createWizardWorld(page: Page, label: string): Promise<void> {
  const name = `${label} ${Date.now()}`;
  const picker = page.getByTestId("wizard-world-select");
  await expect(picker).toBeEnabled();
  await picker.selectOption("__CREATE__");
  await page.getByTestId("wizard-world-new-name").fill(name);
  await page.getByTestId("wizard-world-create-submit").click();
  await expect(page.getByTestId("wizard-world-selected")).toContainText(name);
  await expect(page.getByTestId("wizard-next")).toBeEnabled();
}
