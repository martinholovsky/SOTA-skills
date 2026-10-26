pub fn first_even(v: &[i32]) -> Option<i32> {
    match v.first() { Some(&x) if x % 2 == 0 => Some(x), _ => None }
}
