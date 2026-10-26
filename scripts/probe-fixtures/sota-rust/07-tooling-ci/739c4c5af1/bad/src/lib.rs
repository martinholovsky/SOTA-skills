#![feature(let_chains)]

pub fn first_even(v: &[i32]) -> Option<i32> {
    if let Some(&x) = v.first() && x % 2 == 0 { Some(x) } else { None }
}
