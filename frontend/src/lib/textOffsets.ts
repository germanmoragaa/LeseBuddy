// The backend's token offsets are Unicode code points into the stored original_text (see
// docs/decisions/0003-nlp-pipeline.md). JavaScript string indices (and therefore
// String.prototype.slice) are UTF-16 code units — for any text containing a character outside
// the Basic Multilingual Plane (most emoji, some rare CJK characters), a code point and its
// UTF-16 index diverge, and every token after that character would slice at the wrong
// position. CodePointIndex converts once per article (O(n)) so every token slice afterward is
// O(1) and correct.
//
// Rule: nothing in this app may call `.slice()`/`.substring()` on `original_text` with a raw
// backend offset. Always go through a CodePointIndex first.
export class CodePointIndex {
  private readonly utf16Offsets: number[]

  constructor(text: string) {
    // Array.from(text) iterates by Unicode code point (not UTF-16 code unit), so a
    // surrogate-pair character becomes exactly one array entry — never `text.split('')`,
    // which splits by UTF-16 code unit and would tear surrogate pairs in half.
    const codePoints = Array.from(text)
    const offsets = new Array<number>(codePoints.length + 1)
    let utf16 = 0
    for (let i = 0; i < codePoints.length; i++) {
      offsets[i] = utf16
      utf16 += codePoints[i].length
    }
    offsets[codePoints.length] = utf16
    this.utf16Offsets = offsets
  }

  toUtf16(codePointOffset: number): number {
    return this.utf16Offsets[codePointOffset]
  }

  slice(text: string, codePointStart: number, codePointEnd: number): string {
    return text.slice(this.toUtf16(codePointStart), this.toUtf16(codePointEnd))
  }
}
