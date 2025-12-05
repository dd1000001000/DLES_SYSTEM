import { generateCode } from "../api/code-api";

export class CodeService {
  async generateCode(userCode: string, userInput: string) {
    const res = await generateCode({
      userCode: userCode,
      userInput: userInput,
    });
    return res;
  }
}
