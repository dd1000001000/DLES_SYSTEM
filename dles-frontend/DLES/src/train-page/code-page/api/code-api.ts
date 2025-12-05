import $http from "../../../util/request";
import type { geneCode } from "../type/code-type";

export const generateCode = async (form: geneCode) => {
  const res = await $http.post("/train/code_generation/generate", form);
  return res.data;
};
