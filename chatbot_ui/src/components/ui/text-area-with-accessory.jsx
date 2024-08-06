import * as React from "react";

import { cn } from "@/lib/utils";


const TextareaWithAccessory = React.forwardRef(({ className, children, doNotResize = false, ...props }, ref) => {
  const additionalClasses = doNotResize ? "resize-none" : "";
  return (
    <div
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring focus-visible:ring-offset-2 ",
        className,
      )}
    >
      <textarea
        className={cn(
          "w-full h-full placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none",
          additionalClasses,
        )}
        ref={ref}
        {...props}
      />
      {children}
    </div>
  );
});
TextareaWithAccessory.displayName = "TextareaWithAccessory";

export { TextareaWithAccessory };
