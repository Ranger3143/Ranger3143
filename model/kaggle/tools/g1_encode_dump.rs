// g1_encode_dump - print the engine's token ids for hex-encoded texts, using the REAL aegis-core tokenizer.rs, unmodified.
//
// Build (nothing under aefinity-ai is touched; the file is `include!`d at compile time):
//   TOKENIZER_RS=/path/to/alice-aegis/aegis-core/src/tokenizer.rs rustc --edition 2024 -O g1_encode_dump.rs -o g1_encode_dump
// Run:
//   ./g1_encode_dump VOCAB.BIN < hexlines.txt > ids.txt
// Input: one text per line, as the hex of its UTF-8 bytes. Output: one line per text, comma-separated token ids (an empty line for an empty id list).
extern crate alloc;

mod tokenizer {
    include!(env!("TOKENIZER_RS"));
}

use std::io::{BufRead, Write};
use tokenizer::AegisTokenizer;

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len() / 2).map(|i| u8::from_str_radix(&s[2 * i..2 * i + 2], 16).expect("bad hex")).collect()
}

fn main() {
    let vocab_path = std::env::args().nth(1).expect("usage: g1_encode_dump VOCAB.BIN < hexlines");
    let vocab = std::fs::read(vocab_path).expect("read VOCAB.BIN");
    let tk = AegisTokenizer::new(&vocab).expect("parse VOCAB.BIN");
    let stdin = std::io::stdin();
    let mut out = std::io::BufWriter::new(std::io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let text = String::from_utf8(unhex(line.trim())).expect("input must be UTF-8");
        let ids: Vec<String> = tk.encode(&text).iter().map(|i| i.to_string()).collect();
        writeln!(out, "{}", ids.join(",")).unwrap();
    }
}
