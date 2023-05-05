extern crate rust_unit_wasm;

use rust_unit_wasm::*;

static request_buf: *mut u8;

#[no_mangle]
pub extern "C" fn luw_module_end_handler() {
    //  May not need
}

#[no_mangle]
pub extern "C" fn luw_module_init_handler() {
    //  May not need
}

#[no_mangle]
pub extern "C" fn luw_request_handler(addr: *mut u8) -> i32 {
    let mut ctx_: luw_ctx_t;
    let ctx: *mut luw_ctx_t = &mut ctx_;

    luw_set_req_buf(ctx, &request_buf, LUW_SRB_NONE);

    return 0;
}

pub fn main() {
    //  How to build this without a main function?
}
