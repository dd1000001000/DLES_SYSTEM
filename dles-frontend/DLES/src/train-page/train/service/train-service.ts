import {
  clearCase,
  getInfo,
  deleteCsv,
  uploadCsv,
  evaluate_train,
} from "../api/train-api";
import type { EvaluateParas } from "../type/train-type";

export class TrainService {
  async clearCase(uuid: string) {
    const res = await clearCase(uuid);
    return res;
  }

  async getInfo(uuid: string) {
    const res = await getInfo(uuid);
    return res;
  }

  async deleteCsv(folderName: string, fileName: string) {
    const res = await deleteCsv({ folderName: folderName, fileName: fileName });
    return res;
  }

  async uploadCsv(folderName: string, csvFile: File) {
    const res = await uploadCsv(folderName, csvFile);
    return res;
  }

  async evaluateTrain(folderName: string, paras: EvaluateParas) {
    const res = await evaluate_train(folderName, paras);
    return res;
  }
}
