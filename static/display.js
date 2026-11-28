// Display-only formatting shared by every page. Stored names never change:
// these helpers only decide how a name is shown, so "DIABLOS DEL SOL",
// "Diablos del sol" and "diablos del sol" all read "Diablos del Sol".

const DISPLAY_LOWERCASE_WORDS = new Set(["de", "del", "la", "las", "los", "y", "e", "el", "en"]);

function displayWord(word, index, keepAcronyms) {
    if (!word) return word;
    // Age categories and initialisms keep their capitals: U12, A.C.
    if (/^u\d{1,2}$/i.test(word) || /^([a-z]\.)+[a-z]?\.?$/i.test(word)) return word.toUpperCase();
    // Short all-caps words are acronyms (ECA, FC) unless the whole name was
    // typed in capitals, where "DEL" or "SOL" carry no such meaning.
    if (keepAcronyms && /^\p{Lu}{2,4}$/u.test(word)) return word;
    const lower = word.toLocaleLowerCase("es-MX");
    if (index > 0 && DISPLAY_LOWERCASE_WORDS.has(lower)) return lower;
    // Hyphenated parts are capitalised separately: Ruiz-Esparza. Apostrophes
    // are left alone so possessives read naturally: Kitty’s.
    return lower.replace(/(^|-)(\p{L})/gu, (match, separator, letter) => separator + letter.toLocaleUpperCase("es-MX"));
}

function displayName(name) {
    const text = String(name ?? "").trim().replace(/\s+/g, " ");
    if (!text) return "";
    const words = text.split(" ");
    const typedInCapitals = text === text.toLocaleUpperCase("es-MX");
    const keepAcronyms = !typedInCapitals || words.length === 1;
    return words.map((word, index) => displayWord(word, index, keepAcronyms)).join(" ");
}

function nameInitials(name) {
    const words = displayName(name).split(" ")
        .filter((word) => word && !DISPLAY_LOWERCASE_WORDS.has(word.toLocaleLowerCase("es-MX")));
    const letters = words.slice(0, 2).map((word) => [...word.replace(/[^\p{L}\p{N}]/gu, "")][0] || "");
    return letters.join("").toLocaleUpperCase("es-MX") || "?";
}

if (typeof module !== "undefined") module.exports = {displayName, nameInitials};
