import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import RegistrationForm from "./RegistrationForm";
import LoginForm from "./LoginForm";
import { useAuth } from "../context/AuthContext";

const Layout = ({ children }: { children: React.ReactNode }) => {
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const { isAuthenticated, logoutUser, user } = useAuth();

  return (
        <div className="flex flex-col min-h-screen relative">
      {/* Background Image with Animations */}
      <div
        className="absolute inset-0 bg-cover bg-center z-0"
        style={{
          backgroundImage: `url('/mmino-bg-v4.jpg')`,
          animation: 'floatAnimation 10s ease-in-out infinite, scaleAnimation 10s ease-in-out infinite',
        }}
      ></div>
      <div className="relative z-10 flex flex-col flex-1">
      <header className="sticky top-0 z-50 w-full border-b border-border/40 md:px-8 md:py-0">
        <div className="container flex h-14 max-w-screen-2xl items-center justify-between">
          <a href="/" className="mr-6 flex items-center space-x-2">
            <span className="hidden font-bold sm:inline-block">
              MminoIO
            </span>
          </a>
          <div className="flex items-center justify-end space-x-2">
            {isAuthenticated ? (
              <>
                <span className="mr-2">Welcome, {user?.username || user?.email}!</span>
                <Button onClick={logoutUser}>Logout</Button>
              </>
            ) : (
              <>
                <Button onClick={() => setIsLoginModalOpen(true)}>
                  Login
                </Button>
                <Dialog open={isLoginModalOpen} onOpenChange={setIsLoginModalOpen}>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Login</DialogTitle>
                      <DialogDescription>
                        Log in to your account.
                      </DialogDescription>
                    </DialogHeader>
                    <LoginForm />
                  </DialogContent>
                </Dialog>
                <Button onClick={() => setIsRegisterModalOpen(true)}>
                  Register
                </Button>
                <Dialog open={isRegisterModalOpen} onOpenChange={setIsRegisterModalOpen}>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Register</DialogTitle>
                      <DialogDescription>
                        Create an account to get started.
                      </DialogDescription>
                    </DialogHeader>
                    <RegistrationForm />
                  </DialogContent>
                </Dialog>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 flex items-center justify-center">{children}</main>
      <footer className="py-6 md:px-8 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
          <p className="text-balance text-center text-sm leading-loose text-muted-foreground md:text-left">
            Built by{" "}
            <a
              href="https://tsotetsi.co.za"
              target="_blank"
              rel="noreferrer"
              className="font-medium underline underline-offset-4"
            >
              tsotetsi
            </a>
            . The source code is available on{" "}
            <a
              href=""
              target="_blank"
              rel="noreferrer"
              className="font-medium underline underline-offset-4"
            >
              GitHub
            </a>
            .
          </p>
        </div>
      </footer>
    </div>
  </div>
  );
};

export default Layout;