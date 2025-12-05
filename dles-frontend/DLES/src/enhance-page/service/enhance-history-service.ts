import {
  getEnhanceHistory,
  getDetailedInfo,
  addFolder,
  changeFolderName,
  deleteFolders,
  initCase,
  getCase,
  excuteEnhance,
  downloadCsv,
} from "../api/enhance-history-api";
import type { Dialogue } from "../type/enhance-dialouge-type";

export class EnhanceHistoryService {
  async getEnhanceHistory(username: string) {
    const res = await getEnhanceHistory(username);
    return res;
  }
  async getDetailedInfo(username: string, nodeId: number) {
    const res = await getDetailedInfo(username, nodeId);
    return res;
  }
  async addFolder(username: string, faNodeId: number, nodeName: string) {
    const res = await addFolder(username, {
      faNodeId: faNodeId,
      nodeName: nodeName,
    });
    return res;
  }
  async changeFolderName(
    username: string,
    nodeId: number,
    newNodeName: string,
  ) {
    const res = await changeFolderName(username, {
      nodeId: nodeId,
      newNodeName: newNodeName,
    });
    return res;
  }
  async deleteFolders(username: string, deleteIds: Array<number>) {
    const res = await deleteFolders(username, deleteIds);
    return res;
  }
  async getCase(username: string, nodeId: number) {
    const res = await getCase(username, nodeId);
    return res;
  }
  async initCase(username: string, faNodeId: number, csvFile: File) {
    const res = await initCase(username, faNodeId, csvFile);
    return res;
  }
  async excuteEnhance(
    username: string,
    enhanceId: number,
    dialogues: Dialogue[],
  ) {
    const res = await excuteEnhance(username, enhanceId, dialogues);
    return res;
  }
  async downloadCsv(username: string, enhanceId: number) {
    const res = await downloadCsv(username, enhanceId);
    return res;
  }
}
